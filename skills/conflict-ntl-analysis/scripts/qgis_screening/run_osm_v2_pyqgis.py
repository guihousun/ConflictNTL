"""
PyQGIS OSM v2 Event Screening Pipeline
Run: C:\Program Files\QGIS 3.38.3\apps\Python312\python.exe this_script.py

Uses QGIS native processing for spatial joins; reuses LLM and building filter from old pipeline.
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

QGIS_ROOT = r"C:\Program Files\QGIS 3.38.3"
os.environ["OSGEO4W_ROOT"] = QGIS_ROOT
os.environ["PATH"] = f"{QGIS_ROOT}\\apps\\qgis\\bin;{QGIS_ROOT}\\bin;{os.environ.get('PATH','')}"
sys.path.insert(0, f"{QGIS_ROOT}\\apps\\qgis\\python")

from qgis.core import (
    QgsApplication,
    QgsCoordinateReferenceSystem,
    QgsFeature,
    QgsField,
    QgsFields,
    QgsGeometry,
    QgsPointXY,
    QgsVectorLayer,
)
from qgis.analysis import QgsNativeAlgorithms
import processing
from processing.core.Processing import Processing

import pandas as pd
import geopandas as gpd
from shapely.geometry import Point

BASE = Path(r"D:\Research_vault\raw\writing\conflictntl\data")
OSM_BASE = Path(r"D:\Research_vault\raw\datasets\osm")
OUT = BASE / "event_screening_osm_v2"

EVENTS_CSV = BASE / "source_events" / "ISW_storymap_events_2026-02-27_2026-04-27.csv"
OLD_LLM = BASE / "event_screening_building_filter" / "events_llm_ntl_applicability.csv"
OLD_BUILDING = BASE / "event_screening_building_filter" / "events_5km_building_screening.csv"

EVENT_START = pd.Timestamp("2026-02-27")
EVENT_END = pd.Timestamp("2026-04-21")


def init_qgis():
    qgs = QgsApplication([], False)
    qgs.initQgis()
    Processing.initialize()
    QgsApplication.processingRegistry().addProvider(QgsNativeAlgorithms())
    return qgs


def load_events_csv():
    df = pd.read_csv(EVENTS_CSV, encoding="utf-8-sig")
    df["event_date_parsed"] = pd.to_datetime(df["date"], errors="coerce")
    df["in_window"] = df["event_date_parsed"].between(EVENT_START, EVENT_END, inclusive="both")
    df["lat"] = pd.to_numeric(df["latitude"], errors="coerce")
    df["lon"] = pd.to_numeric(df["longitude"], errors="coerce")
    df["valid_point"] = df["lat"].between(-90, 90) & df["lon"].between(-180, 180)
    return df


def df_to_temp_gpkg(df: pd.DataFrame, path: Path, lat_col="lat", lon_col="lon", id_col="event_id"):
    """Write a DataFrame as a GeoPackage point layer."""
    gdf = gpd.GeoDataFrame(
        df,
        geometry=gpd.points_from_xy(df[lon_col], df[lat_col]),
        crs="EPSG:4326",
    )
    cols = [id_col, "geometry"] + [c for c in df.columns if c not in (id_col, lat_col, lon_col)]
    gdf = gdf[[c for c in cols if c in gdf.columns]]
    gdf.to_file(path, driver="GPKG")
    return gdf


def qgis_join_by_location(input_gpkg: Path, join_gpkg: Path, out_gpkg: Path, join_fields: list[str] = None):
    """Run QGIS native join attributes by location (within)."""
    params = {
        "INPUT": str(input_gpkg),
        "JOIN": str(join_gpkg),
        "PREDICATE": [0],
        "JOIN_FIELDS": join_fields or [],
        "METHOD": 1,
        "DISCARD_NONMATCHING": False,
        "PREFIX": "osm_",
        "OUTPUT": str(out_gpkg),
    }
    result = processing.run("native:joinattributesbylocation", params)
    return result["OUTPUT"]


class UnionFind:
    def __init__(self, n):
        self.parent = list(range(n))
        self.rank = [0] * n

    def find(self, x):
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return
        if self.rank[ra] < self.rank[rb]:
            self.parent[ra] = rb
        elif self.rank[ra] > self.rank[rb]:
            self.parent[rb] = ra
        else:
            self.parent[rb] = ra
            self.rank[ra] += 1


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    tmp = OUT / "_tmp"
    tmp.mkdir(parents=True, exist_ok=True)

    print("Init QGIS...")
    qgs = init_qgis()

    print("Step 0: Load source events")
    events = load_events_csv()
    print(f"  Source rows: {len(events)}")

    print("Step 1: Filter event window + valid points")
    scope = events[events["in_window"] & events["valid_point"]].copy().reset_index(drop=True)
    print(f"  In window + valid: {len(scope)}")

    print("Step 2: OSM gee_geoboundaries ADM0 spatial containment (QGIS)")
    scope_gpkg = tmp / "scope_events.gpkg"
    df_to_temp_gpkg(scope, scope_gpkg, id_col="event_id")

    adm0_gpkg = tmp / "adm0.gpkg"
    adm0 = gpd.GeoDataFrame(
        pd.concat([gpd.read_file(OSM_BASE / "IRN" / "osm_gee_geoboundaries_IRN_adm0.geojson"),
                    gpd.read_file(OSM_BASE / "ISR" / "osm_gee_geoboundaries_ISR_adm0.geojson")],
                   ignore_index=True),
        crs="EPSG:4326",
    )
    adm0 = adm0[["shapeName", "iso3", "geometry"]]
    adm0.to_file(adm0_gpkg, driver="GPKG")

    joined_adm0 = tmp / "scope_adm0.gpkg"
    qgis_join_by_location(scope_gpkg, adm0_gpkg, joined_adm0, join_fields=["shapeName", "iso3"])

    adm0_gdf = gpd.read_file(joined_adm0)
    adm0_gdf = adm0_gdf.rename(columns={"osm_shapeName": "osm_adm0_name", "osm_iso3": "osm_adm0_iso3"})
    adm0_gdf["osm_adm0_matched"] = adm0_gdf["osm_adm0_name"].notna()
    adm0_gdf["in_irn_isr"] = adm0_gdf["osm_adm0_matched"] & adm0_gdf["osm_adm0_iso3"].isin(["IRN", "ISR"])

    adm0_scope = adm0_gdf[adm0_gdf["in_irn_isr"]].copy()
    adm0_scope = adm0_scope.drop(columns=["geometry"])
    print(f"  OSM ADM0 IRN/ISR: {len(adm0_scope)}")

    print("Step 3: OSM ADM1/ADM2 spatial containment (QGIS)")
    for level, irn_path, isr_path in [
        ("adm1", OSM_BASE / "IRN" / "osm_gee_geoboundaries_IRN_adm1.geojson",
         OSM_BASE / "ISR" / "osm_gee_geoboundaries_ISR_adm1.geojson"),
        ("adm2", OSM_BASE / "IRN" / "osm_gee_geoboundaries_IRN_adm2.geojson",
         OSM_BASE / "ISR" / "osm_gee_geoboundaries_ISR_adm2.geojson"),
    ]:
        adm = gpd.GeoDataFrame(
            pd.concat([gpd.read_file(irn_path), gpd.read_file(isr_path)], ignore_index=True),
            crs="EPSG:4326",
        )
        adm = adm[["shapeName", "iso3", "geometry"]]
        adm_gpkg = tmp / f"{level}.gpkg"
        adm.to_file(adm_gpkg, driver="GPKG")

        result_gpkg = tmp / f"scope_{level}.gpkg"
        qgis_join_by_location(scope_gpkg, adm_gpkg, result_gpkg, join_fields=["shapeName", "iso3"])

        result = gpd.read_file(result_gpkg)
        result = result.rename(columns={
            "osm_shapeName": f"osm_{level}_name",
            "osm_iso3": f"osm_{level}_iso3",
        })
        result[f"osm_{level}_matched"] = result[f"osm_{level}_name"].notna()

        summary = result.groupby("event_id").agg(
            **{f"osm_{level}_name": (f"osm_{level}_name", "first"),
               f"osm_{level}_iso3": (f"osm_{level}_iso3", "first"),
               f"osm_{level}_matched": (f"osm_{level}_name", lambda x: x.any())}
        ).reset_index()

        adm0_scope = adm0_scope.merge(summary, on="event_id", how="left")
        adm0_scope[f"osm_{level}_matched"] = adm0_scope[f"osm_{level}_matched"].fillna(False)

    print(f"  ADM1 matched: {adm0_scope['osm_adm1_matched'].sum()}")
    print(f"  ADM2 matched: {adm0_scope['osm_adm2_matched'].sum()}")

    print("Step 4: Reuse LLM labels")
    old_llm = pd.read_csv(OLD_LLM, encoding="utf-8-sig")
    old_llm["_ek"] = old_llm["event_key"].astype(str).str.strip()
    old_llm = old_llm[["_ek", "ntl_relevance_label", "target_category", "confidence", "rationale"]]
    old_llm = old_llm.drop_duplicates(subset=["_ek"], keep="first")
    old_llm = old_llm.rename(columns={
        "ntl_relevance_label": "llm_label",
        "target_category": "llm_target_category",
        "confidence": "llm_confidence",
        "rationale": "llm_rationale",
    })

    adm0_scope["_ek"] = adm0_scope["event_id"].astype(str).str.strip()
    adm0_scope = adm0_scope.merge(old_llm, on="_ek", how="left")
    adm0_scope = adm0_scope.drop(columns=["_ek"])
    adm0_scope["llm_label"] = adm0_scope["llm_label"].fillna("ntl_uncertain")
    adm0_scope["llm_target_category"] = adm0_scope["llm_target_category"].fillna("unknown")
    adm0_scope["llm_confidence"] = adm0_scope["llm_confidence"].fillna("low")
    adm0_scope["llm_rationale"] = adm0_scope["llm_rationale"].fillna("")
    llm_app = (adm0_scope["llm_label"] == "ntl_applicable").sum()
    llm_unc = (adm0_scope["llm_label"] == "ntl_uncertain").sum()
    llm_oss = (adm0_scope["llm_label"] == "out_of_scope").sum()
    print(f"  LLM applicable: {llm_app}, uncertain: {llm_unc}, out_of_scope: {llm_oss}")

    print("Step 5: Reuse building filter results")
    old_bld = pd.read_csv(OLD_BUILDING, encoding="utf-8-sig")
    old_bld["_ek"] = old_bld["event_key"].astype(str).str.strip()
    old_bld = old_bld[["_ek", "building_intersects_5km", "building_intersection_count_5km", "building_filter_method"]]
    old_bld = old_bld.drop_duplicates(subset=["_ek"], keep="first")
    old_bld = old_bld.rename(columns={
        "building_intersects_5km": "building_pass",
        "building_intersection_count_5km": "building_count_5km",
        "building_filter_method": "building_method",
    })

    adm0_scope["_ek"] = adm0_scope["event_id"].astype(str).str.strip()
    adm0_scope = adm0_scope.merge(old_bld, on="_ek", how="left")
    adm0_scope = adm0_scope.drop(columns=["_ek"])
    adm0_scope["building_pass"] = adm0_scope["building_pass"].fillna(False)
    adm0_scope["building_count_5km"] = adm0_scope["building_count_5km"].fillna(0).astype(int)
    adm0_scope["building_method"] = adm0_scope["building_method"].fillna("not_in_old_scope")
    bld_pass = adm0_scope["building_pass"].sum()
    bld_fail = (~adm0_scope["building_pass"]).sum()
    print(f"  Building pass: {bld_pass}, fail: {bld_fail}")

    print("Step 6: Combined filter")
    adm0_scope["downstream"] = adm0_scope["building_pass"] & (adm0_scope["llm_label"] == "ntl_applicable")
    downstream_count = adm0_scope["downstream"].sum()
    excluded_count = len(adm0_scope) - downstream_count
    print(f"  Downstream: {downstream_count}, Excluded: {excluded_count}")

    print("Step 7: Buffer cluster aggregation")
    downstream = adm0_scope[adm0_scope["downstream"]].copy()
    dgdf = gpd.GeoDataFrame(
        downstream,
        geometry=gpd.points_from_xy(downstream["lon"], downstream["lat"]),
        crs="EPSG:4326",
    )

    buffer_results = {}
    for rkm in [5, 10]:
        events_m = dgdf.to_crs("EPSG:3857")
        n = len(events_m)
        uf = UnionFind(n)

        for i in range(n):
            gi = events_m.iloc[i].geometry.centroid
            for j in range(i + 1, n):
                if gi.distance(events_m.iloc[j].geometry.centroid) <= 2 * rkm * 1000:
                    uf.union(i, j)

        cmap = {}
        for i in range(n):
            r = uf.find(i)
            cmap.setdefault(r, []).append(i)

        events_m["cluster_id"] = -1
        for cid, indices in enumerate(sorted(cmap.keys())):
            for idx in indices:
                events_m.iloc[idx, events_m.columns.get_loc("cluster_id")] = cid

        events_wgs = events_m.to_crs("EPSG:4326")
        events_wgs["radius_km"] = int(rkm)
        events_wgs["country"] = downstream["country"].values if "country" in downstream.columns else ""

        cluster_stats = events_wgs.groupby("cluster_id").agg(
            event_count=("event_id", "count"),
            lat=("lat", "mean"),
            lon=("lon", "mean"),
            radius_km=("radius_km", "first"),
        ).reset_index()
        cluster_stats = cluster_stats.sort_values("event_count", ascending=False).reset_index(drop=True)
        cluster_stats["rank"] = range(1, len(cluster_stats) + 1)
        cluster_stats["area_name"] = cluster_stats.apply(
            lambda r: f"Cluster_{r['rank']} ({int(r['event_count'])} events)", axis=1
        )

        membership = events_wgs[["event_id", "cluster_id", "radius_km"]].copy()
        membership = membership.merge(
            cluster_stats[["cluster_id", "rank", "area_name", "event_count"]],
            on="cluster_id", how="left",
        )

        buffer_results[rkm] = {
            "radius_km": rkm,
            "cluster_count": len(cluster_stats),
            "clusters": cluster_stats,
            "membership": membership,
        }
        print(f"  {rkm}km: {len(cluster_stats)} clusters, top5: {cluster_stats.head(5)['event_count'].tolist()}")

    print("Step 8: Export")
    export_cols = [
        "event_id", "event_key", "event_date_utc", "date",
        "country", "latitude", "longitude", "city",
        "event_family", "event_type", "site_type", "site_subtype", "coord_type",
        "has_valid_point", "in_event_window", "in_irn_isr",
        "osm_adm0_name", "osm_adm0_iso3", "osm_adm0_matched",
        "osm_adm1_name", "osm_adm1_iso3", "osm_adm1_matched",
        "osm_adm2_name", "osm_adm2_iso3", "osm_adm2_matched",
        "llm_label", "llm_target_category", "llm_confidence", "llm_rationale",
        "building_pass", "building_count_5km", "building_method",
        "downstream",
    ]
    export_cols = [c for c in export_cols if c in adm0_scope.columns]
    adm0_scope[export_cols].to_csv(OUT / "events_osm_v2_screened.csv", index=False, encoding="utf-8-sig")
    downstream[export_cols].to_csv(OUT / "events_osm_v2_downstream.csv", index=False, encoding="utf-8-sig")

    for rkm, res in buffer_results.items():
        res["clusters"].to_csv(OUT / f"buffer_clusters_{rkm}km.csv", index=False, encoding="utf-8-sig")
        res["membership"].to_csv(OUT / f"buffer_membership_{rkm}km.csv", index=False, encoding="utf-8-sig")

    summary = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "pipeline": "OSM gee_geoboundaries V2 (PyQGIS)",
        "source_events_rows": int(len(events)),
        "step_1_valid_points": int(len(scope)),
        "step_2_adm0_iran_israel": int(len(adm0_scope)),
        "step_3_adm1_matched": int(adm0_scope["osm_adm1_matched"].sum()),
        "step_3_adm2_matched": int(adm0_scope["osm_adm2_matched"].sum()),
        "step_4_llm_applicable": int(llm_app),
        "step_4_llm_uncertain": int(llm_unc),
        "step_4_llm_out_of_scope": int(llm_oss),
        "step_5_building_pass": int(bld_pass),
        "step_6_downstream": int(downstream_count),
        "step_7_buffer_clusters": {
            str(rkm): {
                "cluster_count": res["cluster_count"],
                "top10_event_counts": res["clusters"].head(10)["event_count"].tolist(),
            }
            for rkm, res in buffer_results.items()
        },
    }
    (OUT / "osm_v2_screening_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8",
    )

    print(f"\nDONE. Summary -> {OUT / 'osm_v2_screening_summary.json'}")

    qgs.exitQgis()


if __name__ == "__main__":
    main()
