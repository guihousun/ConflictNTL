"""
geoBoundaries V2 event filtering entrypoint.

This script intentionally does not call the legacy OSM filtering script. It
uses the same high-level filter logic as the manuscript workflow:

1. source ISW/CTP event table;
2. date-window and valid-point filter;
3. geoBoundaries ADM0 spatial containment for Iran and Israel;
4. previously generated HOTOSM building-footprint intersection labels;
5. previously generated LLM NTL-applicability labels;
6. geoBoundaries ADM1/ADM2 labels for downstream reporting context.

The script can run in a QGIS Python environment, but uses GeoPandas for the
spatial joins so it is also usable from a standard geospatial Python stack.
"""

from __future__ import annotations

import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import geopandas as gpd
import pandas as pd


def cfg_path(name: str, default: Path) -> Path:
    return Path(os.environ.get(name, str(default))).expanduser()


PROJECT_ROOT = Path(os.environ.get("CONFLICTNTL_PROJECT_ROOT", Path.cwd())).expanduser()
DATA_ROOT = cfg_path("CONFLICTNTL_DATA_ROOT", PROJECT_ROOT / "data" / "event_screening_geoboundaries_v2_qgis")
INPUT_EVENTS = cfg_path(
    "CONFLICTNTL_EVENTS_CSV",
    PROJECT_ROOT / "inputs" / "ISW_storymap_events_2026-02-27_2026-04-27.csv",
)
LEGACY_DATA_ROOT = cfg_path("CONFLICTNTL_LEGACY_DATA_ROOT", PROJECT_ROOT / "data")
UPSTREAM_DIR = cfg_path("CONFLICTNTL_UPSTREAM_SCREENING_DIR", LEGACY_DATA_ROOT / "event_screening_country_field")
LLM_CSV = cfg_path("CONFLICTNTL_LLM_LABELS_CSV", UPSTREAM_DIR / "events_llm_ntl_applicability.csv")
BUILDING_CSV = cfg_path("CONFLICTNTL_BUILDING_FILTER_CSV", UPSTREAM_DIR / "events_5km_building_screening.csv")
BOUNDARY_CACHE = cfg_path("CONFLICTNTL_BOUNDARY_CACHE_DIR", PROJECT_ROOT / "outputs" / "admin_scale_results" / "geoboundaries_cache")

OUT_SCREENED = cfg_path("CONFLICTNTL_FILTERED_SCREENED_CSV", DATA_ROOT / "events_geoboundaries_v2_screened.csv")
OUT_DOWNSTREAM = cfg_path("CONFLICTNTL_FILTERED_EVENTS_CSV", DATA_ROOT / "events_geoboundaries_v2_downstream.csv")
OUT_SUMMARY = cfg_path("CONFLICTNTL_FILTERING_SUMMARY_JSON", DATA_ROOT / "geoboundaries_v2_screening_summary.json")

EVENT_START = pd.Timestamp(os.environ.get("CONFLICTNTL_EVENT_START", "2026-02-27"))
EVENT_END = pd.Timestamp(os.environ.get("CONFLICTNTL_EVENT_END", "2026-04-21"))
COUNTRIES = ["IRN", "ISR"]
EXPECTED_DOWNSTREAM = os.environ.get("CONFLICTNTL_EXPECTED_FILTERED_EVENTS", "").strip()
STRICT_FILTER_COUNT = os.environ.get("CONFLICTNTL_STRICT_FILTER_COUNT", "").strip().lower() in {"1", "true", "yes"}


def normalize_event_key(series: pd.Series) -> pd.Series:
    text = series.astype(str).str.strip()
    numeric = pd.to_numeric(text, errors="coerce")
    normalized = text.copy()
    ok = numeric.notna()
    normalized.loc[ok] = numeric.loc[ok].round().astype("Int64").astype(str)
    return normalized


def download_geoboundary(iso3: str, adm: int) -> Path | None:
    BOUNDARY_CACHE.mkdir(parents=True, exist_ok=True)
    out = BOUNDARY_CACHE / f"geoBoundaries-{iso3}-ADM{adm}.geojson"
    if out.exists():
        return out
    url = f"https://www.geoboundaries.org/api/current/gbOpen/{iso3}/ADM{adm}/"
    try:
        with urllib.request.urlopen(url, timeout=90) as response:
            meta = json.loads(response.read().decode("utf-8"))
        download_url = meta.get("gjDownloadURL")
        if not download_url:
            raise RuntimeError(f"No gjDownloadURL in geoBoundaries response for {iso3} ADM{adm}")
        urllib.request.urlretrieve(download_url, out)
        return out
    except Exception as exc:
        print(f"boundary_download_failed iso3={iso3} adm={adm}: {exc}")
        return None


def boundary_path(iso3: str, adm: int) -> Path:
    candidates = [
        BOUNDARY_CACHE / f"geoBoundaries-{iso3}-ADM{adm}.geojson",
        BOUNDARY_CACHE / iso3 / f"geoBoundaries-{iso3}-ADM{adm}.geojson",
        BOUNDARY_CACHE / iso3 / f"gee_geoboundaries_{iso3}_adm{adm}.geojson",
    ]
    for path in candidates:
        if path.exists():
            return path
    downloaded = download_geoboundary(iso3, adm)
    if downloaded and downloaded.exists():
        return downloaded
    raise FileNotFoundError(f"Missing geoBoundaries file for {iso3} ADM{adm}; cache={BOUNDARY_CACHE}")


def read_boundaries(adm: int) -> gpd.GeoDataFrame:
    frames = []
    for iso3 in COUNTRIES:
        try:
            gdf = gpd.read_file(boundary_path(iso3, adm)).to_crs("EPSG:4326")
        except FileNotFoundError:
            if adm == 0:
                adm1 = gpd.read_file(boundary_path(iso3, 1)).to_crs("EPSG:4326")
                geom = adm1.geometry.union_all() if hasattr(adm1.geometry, "union_all") else adm1.unary_union
                gdf = gpd.GeoDataFrame({"shapeName": [iso3], "iso3": [iso3]}, geometry=[geom], crs="EPSG:4326")
            else:
                raise
        if "iso3" not in gdf.columns:
            gdf["iso3"] = iso3
        if "shapeName" not in gdf.columns:
            gdf["shapeName"] = iso3
        frames.append(gdf[["shapeName", "iso3", "geometry"]])
    return gpd.GeoDataFrame(pd.concat(frames, ignore_index=True), crs="EPSG:4326")


def load_events() -> pd.DataFrame:
    df = pd.read_csv(INPUT_EVENTS, encoding="utf-8-sig")
    df["event_date_parsed"] = pd.to_datetime(df["date"], errors="coerce")
    df["in_event_window"] = df["event_date_parsed"].between(EVENT_START, EVENT_END, inclusive="both")
    df["latitude"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")
    df["lat"] = df["latitude"]
    df["lon"] = df["longitude"]
    df["has_valid_point"] = df["latitude"].between(-90, 90) & df["longitude"].between(-180, 180)
    return df


def point_gdf(df: pd.DataFrame) -> gpd.GeoDataFrame:
    return gpd.GeoDataFrame(
        df.copy(),
        geometry=gpd.points_from_xy(df["longitude"], df["latitude"]),
        crs="EPSG:4326",
    )


def join_admin(points: gpd.GeoDataFrame, adm: int) -> pd.DataFrame:
    boundaries = read_boundaries(adm)
    joined = gpd.sjoin(
        points[["event_id", "geometry"]],
        boundaries[["shapeName", "iso3", "geometry"]],
        how="left",
        predicate="within",
    )
    summary = (
        joined.groupby("event_id", dropna=False)
        .agg(
            **{
                f"geob_adm{adm}_name": ("shapeName", "first"),
                f"geob_adm{adm}_iso3": ("iso3", "first"),
            }
        )
        .reset_index()
    )
    summary[f"geob_adm{adm}_matched"] = summary[f"geob_adm{adm}_name"].notna()
    return summary


def attach_llm_labels(df: pd.DataFrame) -> pd.DataFrame:
    llm = pd.read_csv(LLM_CSV, encoding="utf-8-sig")
    llm["_ek"] = normalize_event_key(llm["event_key"])
    llm = llm[["_ek", "ntl_relevance_label", "target_category", "confidence", "rationale"]]
    llm = llm.drop_duplicates(subset=["_ek"], keep="first")
    llm = llm.rename(
        columns={
            "ntl_relevance_label": "llm_label",
            "target_category": "llm_target_category",
            "confidence": "llm_confidence",
            "rationale": "llm_rationale",
        }
    )
    df["_ek"] = normalize_event_key(df["event_id"])
    df = df.merge(llm, on="_ek", how="left").drop(columns=["_ek"])
    df["llm_label"] = df["llm_label"].fillna("ntl_uncertain")
    df["llm_target_category"] = df["llm_target_category"].fillna("unknown")
    df["llm_confidence"] = df["llm_confidence"].fillna("low")
    df["llm_rationale"] = df["llm_rationale"].fillna("")
    return df


def attach_building_filter(df: pd.DataFrame) -> pd.DataFrame:
    building = pd.read_csv(BUILDING_CSV, encoding="utf-8-sig")
    building["_ek"] = normalize_event_key(building["event_key"])
    building = building[["_ek", "building_intersects_5km", "building_intersection_count_5km", "building_filter_method"]]
    building = building.drop_duplicates(subset=["_ek"], keep="first")
    building = building.rename(
        columns={
            "building_intersects_5km": "building_pass",
            "building_intersection_count_5km": "building_count_5km",
            "building_filter_method": "building_method",
        }
    )
    df["_ek"] = normalize_event_key(df["event_id"])
    df = df.merge(building, on="_ek", how="left").drop(columns=["_ek"])
    df["building_pass"] = df["building_pass"].fillna(False).infer_objects(copy=False).astype(bool)
    df["building_count_5km"] = df["building_count_5km"].fillna(0).astype(int)
    df["building_method"] = df["building_method"].fillna("not_in_upstream_scope")
    return df


def main() -> None:
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    OUT_SCREENED.parent.mkdir(parents=True, exist_ok=True)
    OUT_DOWNSTREAM.parent.mkdir(parents=True, exist_ok=True)
    OUT_SUMMARY.parent.mkdir(parents=True, exist_ok=True)

    print("Step 0: Load source events")
    events = load_events()
    print(f"  Source rows: {len(events)}")

    print("Step 1: Date window + valid points")
    scope = events[events["in_event_window"] & events["has_valid_point"]].copy().reset_index(drop=True)
    points = point_gdf(scope)
    print(f"  In window + valid: {len(scope)}")

    print("Step 2: geoBoundaries ADM0 spatial containment")
    summary = join_admin(points, 0)
    scope = scope.merge(summary, on="event_id", how="left")
    scope["geob_adm0_matched"] = scope["geob_adm0_matched"].fillna(False)
    print(f"  ADM0 matched: {int(scope['geob_adm0_matched'].sum())}")

    scope["in_irn_isr"] = scope["geob_adm0_matched"] & scope["geob_adm0_iso3"].isin(COUNTRIES)
    scope = scope[scope["in_irn_isr"]].copy()
    print(f"  ADM0 IRN/ISR scope: {len(scope)}")

    print("Step 3: Reuse HOTOSM building filter")
    scope = attach_building_filter(scope)
    building_pass = int(scope["building_pass"].sum())
    print(f"  Building pass: {building_pass}")

    print("Step 4: Reuse LLM NTL applicability labels")
    scope = attach_llm_labels(scope)
    llm_app = int(scope["llm_label"].eq("ntl_applicable").sum())
    llm_unc = int(scope["llm_label"].eq("ntl_uncertain").sum())
    llm_oos = int(scope["llm_label"].eq("out_of_scope").sum())
    print(f"  LLM applicable: {llm_app}, uncertain: {llm_unc}, out_of_scope: {llm_oos}")

    print("Step 5: Combined downstream filter")
    scope["downstream"] = scope["building_pass"] & scope["llm_label"].eq("ntl_applicable")

    print("Step 6: geoBoundaries ADM1/ADM2 labels for reporting context")
    context_points = point_gdf(scope)
    for adm in [1, 2]:
        summary = join_admin(context_points, adm)
        scope = scope.merge(summary, on="event_id", how="left")
        scope[f"geob_adm{adm}_matched"] = scope[f"geob_adm{adm}_matched"].fillna(False)
        print(f"  ADM{adm} matched: {int(scope[f'geob_adm{adm}_matched'].sum())}")

    downstream = scope[scope["downstream"]].copy()
    downstream_count = int(len(downstream))
    expected_count = int(EXPECTED_DOWNSTREAM) if EXPECTED_DOWNSTREAM else None
    count_matches_expected = expected_count is None or downstream_count == expected_count
    print(f"  Downstream: {downstream_count}")
    if expected_count is not None and not count_matches_expected:
        message = f"downstream_count_mismatch expected={expected_count} actual={downstream_count}"
        if STRICT_FILTER_COUNT:
            raise RuntimeError(message)
        print(f"  WARNING: {message}")

    export_cols = [
        "event_id",
        "event_key",
        "event_date_utc",
        "date",
        "country",
        "latitude",
        "longitude",
        "lat",
        "lon",
        "city",
        "event_family",
        "event_type",
        "site_type",
        "site_subtype",
        "coord_type",
        "has_valid_point",
        "in_event_window",
        "in_irn_isr",
        "geob_adm0_name",
        "geob_adm0_iso3",
        "geob_adm0_matched",
        "geob_adm1_name",
        "geob_adm1_iso3",
        "geob_adm1_matched",
        "geob_adm2_name",
        "geob_adm2_iso3",
        "geob_adm2_matched",
        "llm_label",
        "llm_target_category",
        "llm_confidence",
        "llm_rationale",
        "building_pass",
        "building_count_5km",
        "building_method",
        "downstream",
    ]
    export_cols = [col for col in export_cols if col in scope.columns]
    scope[export_cols].to_csv(OUT_SCREENED, index=False, encoding="utf-8-sig")
    downstream[export_cols].to_csv(OUT_DOWNSTREAM, index=False, encoding="utf-8-sig")

    summary = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "pipeline": "geoBoundaries V2 event filtering",
        "source_events_rows": int(len(events)),
        "event_start": str(EVENT_START.date()),
        "event_end": str(EVENT_END.date()),
        "valid_window_points": int(len(points)),
        "adm0_iran_israel": int(len(scope)),
        "adm1_matched": int(scope["geob_adm1_matched"].sum()),
        "adm2_matched": int(scope["geob_adm2_matched"].sum()),
        "llm_applicable": llm_app,
        "llm_uncertain": llm_unc,
        "llm_out_of_scope": llm_oos,
        "building_pass": building_pass,
        "downstream": downstream_count,
        "expected_downstream": expected_count,
        "count_matches_expected": count_matches_expected,
        "outputs": {
            "screened": str(OUT_SCREENED),
            "downstream": str(OUT_DOWNSTREAM),
        },
    }
    OUT_SUMMARY.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"DONE. Summary -> {OUT_SUMMARY}")


if __name__ == "__main__":
    main()
