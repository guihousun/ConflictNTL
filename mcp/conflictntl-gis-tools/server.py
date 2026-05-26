from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP


mcp = FastMCP(
    "conflictntl-gis-tools",
    instructions=(
        "Atomic GIS tools for ConflictNTL-style workflows. These tools provide "
        "boundary download, point-in-polygon filtering, spatial joins, distance "
        "buffers, and dissolved buffer clusters. They do not run the complete "
        "ConflictNTL workflow; a skill or agent must orchestrate the workflow."
    ),
)


def _require_geopandas():
    try:
        import geopandas as gpd
        import pandas as pd
    except Exception as exc:  # pragma: no cover - environment diagnostic
        raise RuntimeError("geopandas and pandas are required for this tool") from exc
    return gpd, pd


def _read_points(path: str, lon_col: str, lat_col: str):
    gpd, pd = _require_geopandas()
    in_path = Path(path).expanduser()
    if in_path.suffix.lower() in {".geojson", ".gpkg", ".shp"}:
        gdf = gpd.read_file(in_path).to_crs("EPSG:4326")
    else:
        df = pd.read_csv(in_path, encoding="utf-8-sig")
        df[lon_col] = pd.to_numeric(df[lon_col], errors="coerce")
        df[lat_col] = pd.to_numeric(df[lat_col], errors="coerce")
        df = df[df[lon_col].between(-180, 180) & df[lat_col].between(-90, 90)].copy()
        gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df[lon_col], df[lat_col]), crs="EPSG:4326")
    return gdf


def _write_vector(gdf, out_path: str) -> dict[str, Any]:
    out = Path(out_path).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.suffix.lower() == ".gpkg":
        gdf.to_file(out, driver="GPKG")
    else:
        gdf.to_file(out, driver="GeoJSON")
    return {"path": str(out), "feature_count": int(len(gdf)), "crs": str(gdf.crs)}


@mcp.tool()
def describe_tools() -> dict[str, Any]:
    """Describe the intended boundary between MCP tools, skills, and scripts."""
    return {
        "server": "conflictntl-gis-tools",
        "role": "atomic reusable GIS/RS/data access abilities",
        "not_role": "complete ConflictNTL workflow runner",
        "use_with_skill": "The ConflictNTL skill decides when to call these tools and when to run workflow-specific scripts.",
        "tools": [
            "validate_environment",
            "download_geoboundary",
            "inspect_vector",
            "filter_points_by_polygon",
            "spatial_join_points_to_admin",
            "make_aeqd_point_buffers",
            "dissolve_overlapping_polygons",
        ],
    }


@mcp.tool()
def validate_environment() -> dict[str, Any]:
    """Check whether the Python GIS dependencies needed by the tools are importable."""
    checks: dict[str, Any] = {"python": sys.executable}
    for module in ["geopandas", "pandas", "shapely", "pyproj", "fiona"]:
        try:
            imported = __import__(module)
            checks[module] = getattr(imported, "__version__", "importable")
        except Exception as exc:
            checks[module] = f"missing: {exc}"
    checks["ok"] = all(not str(value).startswith("missing:") for key, value in checks.items() if key != "python")
    return checks


@mcp.tool()
def download_geoboundary(iso3: str, adm: int, out_dir: str) -> dict[str, Any]:
    """Download one geoBoundaries gbOpen GeoJSON file for an ISO3 code and ADM level."""
    out_root = Path(out_dir).expanduser()
    out_root.mkdir(parents=True, exist_ok=True)
    out = out_root / f"geoBoundaries-{iso3.upper()}-ADM{adm}.geojson"
    if out.exists():
        return {"path": str(out), "downloaded": False}
    api_url = f"https://www.geoboundaries.org/api/current/gbOpen/{iso3.upper()}/ADM{adm}/"
    with urllib.request.urlopen(api_url, timeout=90) as response:
        meta = json.loads(response.read().decode("utf-8"))
    download_url = meta.get("gjDownloadURL")
    if not download_url:
        raise RuntimeError(f"No gjDownloadURL in geoBoundaries response: {api_url}")
    urllib.request.urlretrieve(download_url, out)
    return {"path": str(out), "downloaded": True, "source": download_url}


@mcp.tool()
def inspect_vector(path: str) -> dict[str, Any]:
    """Return basic metadata for a vector dataset."""
    gpd, _ = _require_geopandas()
    gdf = gpd.read_file(Path(path).expanduser())
    bounds = [float(v) for v in gdf.total_bounds]
    return {
        "path": str(Path(path).expanduser()),
        "feature_count": int(len(gdf)),
        "crs": str(gdf.crs),
        "geometry_types": sorted(str(v) for v in gdf.geometry.geom_type.dropna().unique()),
        "columns": [str(c) for c in gdf.columns],
        "bounds": bounds,
    }


@mcp.tool()
def filter_points_by_polygon(
    points_path: str,
    polygon_path: str,
    out_path: str,
    lon_col: str = "longitude",
    lat_col: str = "latitude",
    predicate: str = "within",
) -> dict[str, Any]:
    """Keep points that satisfy a spatial predicate against polygons."""
    gpd, _ = _require_geopandas()
    points = _read_points(points_path, lon_col, lat_col)
    polygons = gpd.read_file(Path(polygon_path).expanduser()).to_crs("EPSG:4326")
    joined = gpd.sjoin(points, polygons[["geometry"]], how="inner", predicate=predicate)
    joined = joined.drop(columns=[c for c in ["index_right"] if c in joined.columns])
    result = joined.drop_duplicates()
    return _write_vector(result, out_path)


@mcp.tool()
def spatial_join_points_to_admin(
    points_path: str,
    admin_path: str,
    out_path: str,
    lon_col: str = "longitude",
    lat_col: str = "latitude",
    admin_name_col: str = "shapeName",
    admin_iso_col: str = "iso3",
    prefix: str = "admin",
) -> dict[str, Any]:
    """Attach admin name/ISO fields to points using point-in-polygon containment."""
    gpd, _ = _require_geopandas()
    points = _read_points(points_path, lon_col, lat_col)
    admin = gpd.read_file(Path(admin_path).expanduser()).to_crs("EPSG:4326")
    keep = ["geometry"]
    for col in [admin_name_col, admin_iso_col]:
        if col in admin.columns:
            keep.append(col)
    joined = gpd.sjoin(points, admin[keep], how="left", predicate="within")
    rename = {}
    if admin_name_col in joined.columns:
        rename[admin_name_col] = f"{prefix}_name"
    if admin_iso_col in joined.columns:
        rename[admin_iso_col] = f"{prefix}_iso3"
    joined = joined.rename(columns=rename).drop(columns=[c for c in ["index_right"] if c in joined.columns])
    joined[f"{prefix}_matched"] = joined.get(f"{prefix}_name").notna() if f"{prefix}_name" in joined.columns else False
    return _write_vector(joined, out_path)


@mcp.tool()
def make_aeqd_point_buffers(
    points_path: str,
    out_path: str,
    radius_km: float,
    lon_col: str = "longitude",
    lat_col: str = "latitude",
) -> dict[str, Any]:
    """Create equal-distance AEQD buffers around points and write polygons."""
    gpd, _ = _require_geopandas()
    points = _read_points(points_path, lon_col, lat_col)
    lon0 = float(points.geometry.x.mean())
    lat0 = float(points.geometry.y.mean())
    aeqd = f"+proj=aeqd +lat_0={lat0} +lon_0={lon0} +datum=WGS84 +units=m +no_defs"
    buffered = points.to_crs(aeqd).copy()
    buffered["geometry"] = buffered.geometry.buffer(float(radius_km) * 1000.0)
    buffered = buffered.to_crs("EPSG:4326")
    result = _write_vector(buffered, out_path)
    result.update({"radius_km": float(radius_km), "aeqd_lon0": lon0, "aeqd_lat0": lat0})
    return result


@mcp.tool()
def dissolve_overlapping_polygons(polygons_path: str, out_path: str, id_col: str = "cluster_id") -> dict[str, Any]:
    """Dissolve intersecting polygons into connected components."""
    gpd, _ = _require_geopandas()
    gdf = gpd.read_file(Path(polygons_path).expanduser())
    if gdf.crs is None:
        raise RuntimeError("Input polygons must have a CRS.")
    sindex = gdf.sindex
    visited: set[int] = set()
    component_ids = [-1] * len(gdf)
    component = 0
    for start in range(len(gdf)):
        if start in visited:
            continue
        stack = [start]
        visited.add(start)
        while stack:
            current = stack.pop()
            component_ids[current] = component
            geom = gdf.geometry.iloc[current]
            for candidate in sindex.query(geom, predicate="intersects"):
                candidate = int(candidate)
                if candidate not in visited:
                    visited.add(candidate)
                    stack.append(candidate)
        component += 1
    tmp = gdf.copy()
    tmp[id_col] = component_ids
    dissolved = tmp.dissolve(by=id_col).reset_index()
    dissolved["member_count"] = tmp.groupby(id_col).size().values
    return _write_vector(dissolved, out_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="ConflictNTL atomic GIS MCP tools")
    parser.add_argument("--transport", choices=["stdio", "sse", "streamable-http"], default="stdio")
    parser.add_argument("--mount-path", default=None)
    args = parser.parse_args()
    mcp.run(transport=args.transport, mount_path=args.mount_path)


if __name__ == "__main__":
    main()
