from __future__ import annotations

from pathlib import Path

import geopandas as gpd
import pandas as pd
from pyproj import CRS
from shapely.ops import unary_union


DATA = Path(r"D:\Research_vault\raw\writing\conflictntl\data")
EVENTS = DATA / "event_screening_geoboundaries_v2_qgis" / "events_osm_v2_downstream.csv"
CURRENT_MEMBERSHIP = DATA / "event_screening_geoboundaries" / "buffer_membership_5km.csv"
CURRENT_CLUSTERS = DATA / "event_screening_geoboundaries" / "buffer_clusters_5km.csv"
METRICS = DATA / "event_screening_geoboundaries" / "buffer_ntl_v2" / "v2_buffer_5km_change_metrics.csv"


class UnionFind:
    def __init__(self, n: int) -> None:
        self.parent = list(range(n))
        self.rank = [0] * n

    def find(self, x: int) -> int:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: int, b: int) -> None:
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


def mode_or_blank(values: pd.Series) -> str:
    modes = values.dropna().mode()
    return str(modes.iloc[0]) if len(modes) else ""


def recalc_distance_components(events_gdf: gpd.GeoDataFrame, epsg: str) -> pd.DataFrame:
    metric = events_gdf.to_crs(epsg).reset_index(drop=True)
    geoms = metric.geometry
    sindex = metric.sindex
    uf = UnionFind(len(metric))
    for i, geom in enumerate(geoms):
        for j in sindex.query(geom.buffer(10000), predicate="intersects"):
            if j <= i:
                continue
            if geom.distance(geoms.iloc[int(j)]) <= 10000:
                uf.union(i, int(j))
    roots = [uf.find(i) for i in range(len(metric))]
    rows = pd.DataFrame(
        {
            "row_index": range(len(metric)),
            "root": roots,
            "event_id": metric["event_id"].values,
            "country": metric["country"].values,
        }
    )
    counts = (
        rows.groupby("root")
        .agg(
            row_n=("event_id", "size"),
            unique_event_id_n=("event_id", "nunique"),
            country_mode=("country", mode_or_blank),
        )
        .reset_index()
        .sort_values("row_n", ascending=False)
        .reset_index(drop=True)
    )
    counts["rank"] = range(1, len(counts) + 1)
    return counts


def recalc_buffer_union(events_gdf: gpd.GeoDataFrame, epsg: str) -> pd.DataFrame:
    metric = events_gdf.to_crs(epsg).reset_index(drop=True)
    buffers = metric.geometry.buffer(5000)
    merged = unary_union(list(buffers))
    polys = list(merged.geoms) if merged.geom_type == "MultiPolygon" else [merged]
    poly_gdf = gpd.GeoDataFrame({"poly_id": range(len(polys))}, geometry=polys, crs=epsg)
    joined = gpd.sjoin(metric[["event_id", "country", "geometry"]], poly_gdf, how="left", predicate="within")
    counts = (
        joined.groupby("poly_id")
        .agg(
            row_n=("event_id", "size"),
            unique_event_id_n=("event_id", "nunique"),
            country_mode=("country", mode_or_blank),
        )
        .reset_index()
        .sort_values("row_n", ascending=False)
        .reset_index(drop=True)
    )
    counts["rank"] = range(1, len(counts) + 1)
    return counts


def main() -> None:
    events = pd.read_csv(EVENTS, encoding="utf-8-sig")
    events["latitude"] = pd.to_numeric(events["latitude"], errors="coerce")
    events["longitude"] = pd.to_numeric(events["longitude"], errors="coerce")
    events = events.dropna(subset=["latitude", "longitude"]).reset_index(drop=True)
    gdf = gpd.GeoDataFrame(
        events,
        geometry=gpd.points_from_xy(events["longitude"], events["latitude"]),
        crs="EPSG:4326",
    )
    lon0 = float(gdf["longitude"].mean())
    lat0 = float(gdf["latitude"].mean())
    aeqd = CRS.from_proj4(
        f"+proj=aeqd +lat_0={lat0:.8f} +lon_0={lon0:.8f} +datum=WGS84 +units=m +no_defs"
    )

    print(f"SOURCE rows={len(gdf)} unique_event_id={gdf['event_id'].nunique()}")
    print(f"AEQD center lon0={lon0:.6f} lat0={lat0:.6f}")
    print("DUPLICATE event_id rows:")
    duplicate_cols = ["event_id", "country", "city", "latitude", "longitude", "event_type"]
    print(gdf[gdf["event_id"].duplicated(keep=False)][duplicate_cols].to_string(index=False))

    projections = [
        ("AEQD_STUDY_CENTER", aeqd),
        ("EPSG:3857", "EPSG:3857"),
        ("EPSG:6933", "EPSG:6933"),
    ]

    for name, crs in projections:
        counts = recalc_distance_components(gdf, crs)
        print(f"\nPOINT_DISTANCE {name} clusters={len(counts)}")
        print(counts.head(12)[["rank", "root", "country_mode", "row_n", "unique_event_id_n"]].to_string(index=False))

    for name, crs in projections:
        counts = recalc_buffer_union(gdf, crs)
        print(f"\nBUFFER_UNION {name} clusters={len(counts)}")
        print(counts.head(12)[["rank", "poly_id", "country_mode", "row_n", "unique_event_id_n"]].to_string(index=False))

    membership = pd.read_csv(CURRENT_MEMBERSHIP, encoding="utf-8-sig")
    clusters = pd.read_csv(CURRENT_CLUSTERS, encoding="utf-8-sig")
    metrics = pd.read_csv(METRICS, encoding="utf-8-sig")

    print(f"\nCURRENT_CLUSTER_TABLE clusters={len(clusters)}")
    print(clusters.sort_values("rank").head(12)[["rank", "cluster_id", "event_count", "area_name"]].to_string(index=False))

    top = metrics.sort_values("rank").head(10)[["rank", "cluster_id", "country_mode", "event_count_total"]]
    counts = (
        membership.groupby("cluster_id")
        .agg(row_n=("event_id", "size"), unique_event_id_n=("event_id", "nunique"))
        .reset_index()
    )
    print("\nCURRENT_TOP10_FROM_MEMBERSHIP")
    print(top.merge(counts, on="cluster_id", how="left").to_string(index=False))


if __name__ == "__main__":
    main()
