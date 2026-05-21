"""
Export an extra Figure 3 composite with top-10 5 km core-impact overlays.

The overlay shows the actual dissolved 5 km buffer-cluster footprints rather
than equal-size point markers, so the spatial extent of each core-impact area is
visible while the underlying NTL raster remains readable. This script does not
overwrite the main Figure 3 composite.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import geopandas as gpd
import matplotlib.patheffects as pe
import pandas as pd
from shapely.geometry import box


HERE = Path(__file__).resolve().parent
EXPORTER_PATH = HERE / "export_figure3_v2_admin_ntl_panel_assets.py"
LEGACY_DATA = Path(r"D:\Research_vault\raw\writing\conflictntl\data\event_screening_geoboundaries")
AEQD_BUFFER_NTL = (
    Path(r"D:\Research_vault\raw\writing\conflictntl\data")
    / "event_screening_geoboundaries_v2_qgis"
    / "buffer_ntl_aeqd5"
)
AEQD_TOP10_GEOJSON = AEQD_BUFFER_NTL / "aeqd_5km_top10_clusters.geojson"
TEXT_SCALE = 1.0


def load_exporter():
    spec = importlib.util.spec_from_file_location("figure3_exporter", EXPORTER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {EXPORTER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_top10_core_polygons() -> pd.DataFrame:
    if AEQD_TOP10_GEOJSON.exists():
        out = gpd.read_file(AEQD_TOP10_GEOJSON).to_crs("EPSG:4326")
        out["rank"] = out["rank"].astype(int)
        return out.sort_values("rank").reset_index(drop=True)

    raise FileNotFoundError(
        f"Missing AEQD top10 cluster polygons: {AEQD_TOP10_GEOJSON}. "
        "Run make_table1_aeqd_5km_clusters_ntl_complete.py first."
    )


def iter_line_geometries(geom):
    if geom.is_empty:
        return
    geom_type = geom.geom_type
    if geom_type == "LineString":
        yield geom
    elif geom_type == "MultiLineString":
        yield from geom.geoms
    elif geom_type == "GeometryCollection":
        for part in geom.geoms:
            yield from iter_line_geometries(part)
    elif hasattr(geom, "boundary"):
        yield from iter_line_geometries(geom.boundary)


def overlay_core_polygons(
    ax,
    cores: pd.DataFrame,
    iso3: str,
    *,
    zoom: bool = False,
    show_labels: bool = False,
    label_offsets: dict[int, tuple[float, float]] | None = None,
    linewidth_scale: float = 1.0,
) -> None:
    country = "Iran" if iso3 == "IRN" else "Israel"
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    viewport = box(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))
    scoped = cores[cores["country_mode"] == country].copy()
    scoped = scoped[scoped["geometry"].map(lambda geom: geom.intersects(viewport))]
    if scoped.empty:
        return

    line_width = (0.78 if zoom else 0.56) * linewidth_scale
    halo_width = (1.28 if zoom else 1.02) * linewidth_scale
    label_size = 11.1 * TEXT_SCALE
    dx = 0.012 * abs(x1 - x0)
    dy = 0.012 * abs(y1 - y0)
    for row in scoped.itertuples(index=False):
        geometry = row.geometry
        for line in iter_line_geometries(geometry.boundary):
            xs, ys = line.xy
            drawn = ax.plot(
                xs,
                ys,
                color="#111111",
                linewidth=line_width,
                linestyle=(0, (3.0, 1.7)),
                alpha=0.9,
                zorder=31,
                solid_capstyle="round",
                solid_joinstyle="round",
                clip_on=True,
            )[0]
            drawn.set_path_effects([pe.withStroke(linewidth=halo_width, foreground="white")])
        if not show_labels:
            continue
        anchor = geometry.representative_point()
        rank = int(row.rank)
        extra_dx, extra_dy = (label_offsets or {}).get(rank, (0.0, 0.0))
        ax.text(
            anchor.x + dx + extra_dx * abs(x1 - x0),
            anchor.y + dy + extra_dy * abs(y1 - y0),
            str(rank),
            fontsize=label_size,
            fontweight="bold",
            ha="left",
            va="bottom",
            color="#111111",
            zorder=33,
            path_effects=[pe.withStroke(linewidth=1.35, foreground="white")],
        )


def draw_overlay_composite(exporter, cores: pd.DataFrame, *, show_labels: bool, out_name: str) -> None:
    irn_adm0, irn_adm1, irn_bounds = exporter.load_boundaries("IRN")
    isr_adm0, isr_adm1, isr_bounds = exporter.load_boundaries("ISR")

    fig = exporter.plt.figure(figsize=(8.1, 7.05), dpi=450)
    axes = {
        "a": fig.add_axes([0.055, 0.688, 0.300, 0.245]),
        "b": fig.add_axes([0.345, 0.688, 0.300, 0.245]),
        "c": fig.add_axes([0.635, 0.688, 0.300, 0.245]),
        "d": fig.add_axes([0.055, 0.185, 0.172, 0.475]),
        "e": fig.add_axes([0.228, 0.185, 0.172, 0.475]),
        "f": fig.add_axes([0.401, 0.185, 0.172, 0.475]),
        "g": fig.add_axes([0.635, 0.450, 0.300, 0.210]),
        "h": fig.add_axes([0.635, 0.185, 0.300, 0.210]),
    }

    exporter.plot_panel_on_ax(
        axes["a"], "IRN", 1, "mean", irn_adm0, irn_adm1, irn_bounds, 500,
        tick_labelsize=9.6, scale_fontsize=10.5,
    )
    exporter.plot_panel_on_ax(axes["b"], "IRN", 2, "mean", irn_adm0, irn_adm1, irn_bounds, None, tick_labelsize=9.6)
    exporter.plot_panel_on_ax(axes["c"], "IRN", 4, "diff", irn_adm0, irn_adm1, irn_bounds, None, tick_labelsize=9.6)
    exporter.plot_panel_on_ax(
        axes["d"], "ISR", 1, "mean", isr_adm0, isr_adm1, isr_bounds, 50, "top-left",
        tick_labelsize=9.6, scale_fontsize=10.5,
    )
    exporter.plot_panel_on_ax(axes["e"], "ISR", 2, "mean", isr_adm0, isr_adm1, isr_bounds, None, tick_labelsize=9.6)
    exporter.plot_panel_on_ax(axes["f"], "ISR", 4, "diff", isr_adm0, isr_adm1, isr_bounds, None, tick_labelsize=9.6)
    exporter.plot_zoom_on_ax(axes["g"], "IRN", exporter.IRAN_ZOOM, irn_adm0, irn_adm1, irn_bounds)
    exporter.plot_zoom_on_ax(axes["h"], "ISR", exporter.ISRAEL_ZOOM, isr_adm0, isr_adm1, isr_bounds)

    for key in ["b", "c", "e", "f"]:
        axes[key].tick_params(axis="y", labelleft=False)

    overlay_core_polygons(
        axes["c"],
        cores,
        "IRN",
        show_labels=show_labels,
        label_offsets={2: (-0.060, 0.020), 10: (0.020, -0.020)},
    )
    overlay_core_polygons(axes["f"], cores, "ISR", show_labels=show_labels)
    overlay_core_polygons(axes["g"], cores, "IRN", zoom=True, show_labels=show_labels)
    overlay_core_polygons(axes["h"], cores, "ISR", zoom=True, show_labels=show_labels)

    exporter.add_zoom_box(axes["c"], exporter.IRAN_ZOOM)
    exporter.add_zoom_box(axes["f"], exporter.ISRAEL_ZOOM)
    exporter.add_composite_colorbar(
        fig,
        [0.055, 0.118, 0.405, 0.016],
        exporter.MEAN_BREAKS,
        exporter.MEAN_COLORS,
        "NTL intensity (nW/cm$^2$/sr)",
    )
    exporter.add_composite_colorbar(
        fig,
        [0.530, 0.118, 0.405, 0.016],
        exporter.DIFF_BREAKS,
        exporter.DIFF_COLORS,
        "NTL intensity difference (nW/cm$^2$/sr)",
        ticks=[-10, -3, 3, 10],
    )

    out = exporter.OUT_DIR / out_name
    fig.savefig(out, dpi=450, bbox_inches="tight", pad_inches=0.04)
    exporter.plt.close(fig)
    print(f"Wrote {out}")


def main() -> None:
    exporter = load_exporter()
    exporter.DIFF_BREAKS = [-1e9, -10, -3, 3, 10, 1e9]
    exporter.DIFF_COLORS = ["#253494", "#7fcdbb", "#fff2d8", "#fdae61", "#d73027"]
    exporter.TILE_DIR = exporter.OUT_DIR / "_tiles_diff_5class_10_3_3_10"
    # Match the Tehran zoom panel aspect ratio so panel h renders the same visual width as panel g.
    exporter.ISRAEL_ZOOM = (34.62, 31.94, 35.03, 32.225)
    exporter.configure_matplotlib()
    cores = load_top10_core_polygons()
    draw_overlay_composite(
        exporter,
        cores,
        show_labels=True,
        out_name="figure3_v2_admin_ntl_composite_diff_5class_10_3_3_10_aeqd_top10_core_polygons_ranked.png",
    )
    draw_overlay_composite(
        exporter,
        cores,
        show_labels=False,
        out_name="figure3_v2_admin_ntl_composite_diff_5class_10_3_3_10_aeqd_top10_core_polygons.png",
    )


if __name__ == "__main__":
    main()
