"""Convert all geoboundaries GeoJSON to SHP.
Filters out non-polygon (LINESTRING, POINT) features for SHP compatibility.
"""
import geopandas as gpd
from pathlib import Path
from shapely.geometry import Polygon, MultiPolygon

GEOB = Path(r"D:\Research_vault\raw\datasets\geoboundaries")

POLYGON_TYPES = (Polygon, MultiPolygon)

for country_dir in sorted(GEOB.iterdir()):
    if not country_dir.is_dir():
        continue
    for geojson_file in sorted(country_dir.glob("*.geojson")):
        shp_file = geojson_file.with_suffix(".shp")

        gdf = gpd.read_file(geojson_file)

        # Filter: keep only POLYGON / MULTIPOLYGON geometries
        mask = gdf.geometry.apply(lambda g: isinstance(g, POLYGON_TYPES))
        dropped = (~mask).sum()
        if dropped > 0:
            gdf = gdf[mask].copy()
            print(f"  WARN: {geojson_file.name} — dropped {dropped} non-polygon features")

        if len(gdf) == 0:
            print(f"  SKIP: {geojson_file.name} — no polygon features remain")
            continue

        # Truncate long column names for SHP compatibility
        short_cols = {}
        for col in gdf.columns:
            if col != "geometry" and len(col) > 10:
                short_cols[col] = col[:10]
        if short_cols:
            gdf = gdf.rename(columns=short_cols)

        # Delete any stale SHP parts from previous failed runs
        for ext in (".shp", ".shx", ".dbf", ".prj", ".cpg"):
            part = geojson_file.with_suffix(ext)
            if part.exists():
                part.unlink()

        gdf.to_file(shp_file)
        mb = shp_file.stat().st_size / (1024 * 1024)
        print(f"  OK: {shp_file.name}  ({mb:.1f} MB, {len(gdf)} features)")

print("\nDONE")
