from __future__ import annotations

import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

import geopandas as gpd
import pandas as pd


DATA_DIR = Path(r"D:\Research_vault\raw\datasets\osm\geofabrik")
OUT_DIR = Path(r"D:\Research_vault\raw\datasets\osm\conflictntl")
OUT_GPKG = OUT_DIR / "conflictntl_osm_admin_boundaries.gpkg"
OUT_META = OUT_DIR / "conflictntl_osm_admin_boundaries_metadata.json"

DOWNLOADS = {
    "iran": {
        "url": "https://download.geofabrik.de/asia/iran-latest-free.gpkg.zip",
        "zip": DATA_DIR / "iran-latest-free.gpkg.zip",
        "gpkg_dir": DATA_DIR / "iran-latest-free.gpkg",
        "gpkg": DATA_DIR / "iran-latest-free.gpkg" / "iran.gpkg",
    },
    "israel_palestine": {
        "url": "https://download.geofabrik.de/asia/israel-and-palestine-latest-free.gpkg.zip",
        "zip": DATA_DIR / "israel-and-palestine-latest-free.gpkg.zip",
        "gpkg_dir": DATA_DIR / "israel-and-palestine-latest-free.gpkg",
        "gpkg": DATA_DIR / "israel-and-palestine-latest-free.gpkg" / "israel-and-palestine.gpkg",
    },
}


def download_if_needed(name: str, cfg: dict[str, object]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    target = Path(cfg["zip"])
    if target.exists() and target.stat().st_size > 1_000_000:
        return
    tmp = target.with_suffix(target.suffix + ".part")
    req = Request(str(cfg["url"]), headers={"User-Agent": "ConflictNTL OSM boundary cache"})
    with urlopen(req, timeout=120) as response, tmp.open("wb") as handle:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            handle.write(chunk)
    tmp.replace(target)


def extract_if_needed(cfg: dict[str, object]) -> None:
    gpkg = Path(cfg["gpkg"])
    if gpkg.exists() and gpkg.stat().st_size > 1_000_000:
        return
    gpkg.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(Path(cfg["zip"])) as archive:
        archive.extractall(Path(cfg["gpkg_dir"]))


def read_adminareas(cfg: dict[str, object]) -> gpd.GeoDataFrame:
    return gpd.read_file(Path(cfg["gpkg"]), layer="gis_osm_adminareas_a_free").to_crs("EPSG:4326")


def normalize(sub: gpd.GeoDataFrame, country: str, iso3: str, adm_level: str, osm_admin_level: int) -> gpd.GeoDataFrame:
    out = sub.copy()
    out["country"] = country
    out["country_iso3"] = iso3
    out["adm_level"] = adm_level
    out["osm_admin_level"] = osm_admin_level
    out["osm_name"] = out["name"].astype(str)
    out["osm_id"] = out["osm_id"].astype(str)
    out["source"] = "Geofabrik OpenStreetMap free GeoPackage"
    return out[
        [
            "country",
            "country_iso3",
            "adm_level",
            "osm_admin_level",
            "osm_id",
            "osm_name",
            "fclass",
            "code",
            "source",
            "geometry",
        ]
    ]


def build_boundaries() -> gpd.GeoDataFrame:
    for name, cfg in DOWNLOADS.items():
        download_if_needed(name, cfg)
        extract_if_needed(cfg)

    iran = read_adminareas(DOWNLOADS["iran"])
    israel = read_adminareas(DOWNLOADS["israel_palestine"])

    # ADM1 / ADM2
    iran_adm1 = normalize(iran[iran["fclass"].eq("admin_level4")], "Iran", "IRN", "ADM1", 4)
    iran_adm2 = normalize(iran[iran["fclass"].eq("admin_level5")], "Iran", "IRN", "ADM2", 5)

    iran_adm0 = normalize(
        gpd.GeoDataFrame(
            {"name": ["Iran"], "osm_id": ["IRN_national"], "fclass": ["national"], "code": [""]},
            geometry=[iran_adm1.dissolve().geometry.buffer(0).iloc[0]],
            crs="EPSG:4326",
        ),
        "Iran", "IRN", "ADM0", 2,
    )

    # Israel: keep Hebrew-prefixed districts/subdistricts only, exclude Palestinian areas
    israel_adm1_src = israel[israel["fclass"].eq("admin_level4") & israel["name"].astype(str).str.startswith("מחוז")]
    israel_adm2_src = israel[israel["fclass"].eq("admin_level5") & israel["name"].astype(str).str.startswith("נפת")]
    israel_adm1 = normalize(israel_adm1_src, "Israel", "ISR", "ADM1", 4)
    israel_adm2 = normalize(israel_adm2_src, "Israel", "ISR", "ADM2", 5)

    israel_adm0 = normalize(
        gpd.GeoDataFrame(
            {"name": ["Israel"], "osm_id": ["ISR_national"], "fclass": ["national"], "code": [""]},
            geometry=[israel_adm1.dissolve().geometry.buffer(0).iloc[0]],
            crs="EPSG:4326",
        ),
        "Israel", "ISR", "ADM0", 2,
    )

    combined = gpd.GeoDataFrame(
        pd.concat([iran_adm0, iran_adm1, iran_adm2, israel_adm0, israel_adm1, israel_adm2], ignore_index=True),
        geometry="geometry",
        crs="EPSG:4326",
    )
    combined = combined[combined.geometry.notna() & ~combined.geometry.is_empty].copy()
    combined["area_km2"] = combined.to_crs("EPSG:6933").geometry.area / 1_000_000
    return combined


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    boundaries = build_boundaries()
    if OUT_GPKG.exists():
        OUT_GPKG.unlink()
    boundaries.to_file(OUT_GPKG, layer="admin_boundaries", driver="GPKG")
    counts = {
        f"{country}_{adm_level}": int(count)
        for (country, adm_level), count in boundaries.groupby(["country", "adm_level"]).size().items()
    }
    summary = {
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "output": str(OUT_GPKG),
        "downloads": {k: {"url": v["url"], "zip": str(v["zip"]), "gpkg": str(v["gpkg"])} for k, v in DOWNLOADS.items()},
        "counts": counts,
        "note": "ADM1/ADM2 are derived directly from Geofabrik OpenStreetMap free GeoPackages. Iran uses OSM admin_level 4/5; Israel uses OSM admin_level 4/5 filtered to Hebrew district/subdistrict names.",
    }
    OUT_META.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
