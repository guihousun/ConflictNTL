"""
Export an alternate manuscript Figure 3 with 7-bin NTL color scales.

This version keeps the current publication layout and 3 km top-10 cluster
overlay, but refreshes/reuses GEE-rendered PNG tiles so the raster coverage stays
consistent with the existing Figure 3 workflow. Mean NTL panels omit ADM1
internal boundaries; difference panels and zooms retain ADM1 context.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import matplotlib as mpl
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.patches import ConnectionPatch


HERE = Path(__file__).resolve().parent
OVERLAY_PATH = HERE / "export_figure3_v2_admin_ntl_top10_core_overlay.py"
ATTACH = Path(r"D:\Research_vault\raw\writing\conflictntl\attachments")
TOP10_3KM = (
    Path(r"D:\Research_vault\raw\writing\conflictntl\data")
    / "event_screening_geoboundaries_v2_qgis"
    / "buffer_ntl_aeqd3"
    / "aeqd_3km_top10_clusters.geojson"
)

TEXT_SCALE = 1.3
OUT_NO_REDLINES = ATTACH / "Fig3_0518v4_text13_7band_no_admin_no_redlines.png"

MEAN_BREAKS = [0, 3, 7, 10, 20, 50, 80, 255]
MEAN_COLORS = ["#000000", "#242424", "#464646", "#707070", "#9a9a9a", "#c5c5c5", "#ffffff"]
DIFF_BREAKS = [-1e9, -10, -5, -3, 3, 5, 10, 1e9]
DIFF_COLORS = ["#1f2f99", "#2c7fb8", "#7fcdbb", "#fff2d8", "#fdae61", "#f46d43", "#d73027"]


def load_overlay_module():
    spec = importlib.util.spec_from_file_location("figure3_overlay_base", OVERLAY_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {OVERLAY_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def configure_exporter(exporter):
    exporter.MEAN_BREAKS = MEAN_BREAKS
    exporter.MEAN_COLORS = MEAN_COLORS
    exporter.DIFF_BREAKS = DIFF_BREAKS
    exporter.DIFF_COLORS = DIFF_COLORS
    exporter.TILE_DIR = exporter.OUT_DIR / "_tiles_mean7_diff7_0_3_7_10_20_50_80_255_pm10_3_1"
    exporter.ISRAEL_ZOOM = (34.62, 31.94, 35.03, 32.225)
    exporter.configure_matplotlib()
    exporter.TILE_DIR.mkdir(parents=True, exist_ok=True)
    return exporter


def refresh_tiles_if_needed(exporter, irn_adm1, irn_bounds, isr_adm1, isr_bounds) -> None:
    expected = [
        exporter.TILE_DIR / f"{iso3}_{panel_idx}_{kind}_asset_v2.png"
        for iso3 in ["IRN", "ISR"]
        for panel_idx, kind in [(1, "mean"), (2, "mean"), (4, "diff")]
    ]
    if all(path.exists() and path.stat().st_size > 1000 for path in expected):
        return

    exporter.init_gee()
    base = exporter.load_base_module()
    exporter.refresh_tiles_for_country(base, "IRN", irn_adm1, irn_bounds)
    exporter.refresh_tiles_for_country(base, "ISR", isr_adm1, isr_bounds)


def add_panel_label(ax, label: str, loc: str = "upper-right") -> None:
    if loc == "upper-left":
        xy = (0.06, 0.95)
        ha = "left"
    else:
        xy = (0.94, 0.95)
        ha = "right"
    ax.text(
        *xy,
        label,
        transform=ax.transAxes,
        ha=ha,
        va="top",
        fontsize=13.0 * TEXT_SCALE,
        color="black",
        zorder=50,
    )


def add_zoom_name(ax, text: str, loc: str) -> None:
    if loc == "bottom-right":
        xy = (0.95, 0.07)
        ha = "right"
        va = "bottom"
    else:
        xy = (0.04, 0.92)
        ha = "left"
        va = "top"
    ax.text(
        *xy,
        text,
        transform=ax.transAxes,
        ha=ha,
        va=va,
        fontsize=11.0 * TEXT_SCALE,
        fontweight="bold",
        color="black",
        zorder=60,
        linespacing=0.82,
        bbox={"facecolor": "#c9c9c9", "edgecolor": "none", "alpha": 0.82, "pad": 1.0},
    )


def add_top_left_scale_bar_low(exporter, ax, km: float, fontsize: float) -> None:
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    lat = y1 - 0.20 * (y1 - y0)
    length = exporter.degree_len_for_km(km, lat)
    start = x0 + 0.10 * (x1 - x0)
    end = start + length
    ax.plot([start, end], [lat, lat], color="black", lw=1.35, solid_capstyle="butt", zorder=8)
    tick = 0.018 * (y1 - y0)
    ax.plot([start, start], [lat - tick, lat + tick], color="black", lw=0.85, zorder=8)
    ax.plot([end, end], [lat - tick, lat + tick], color="black", lw=0.85, zorder=8)
    ax.text(
        (start + end) / 2,
        lat - 0.055 * (y1 - y0),
        f"{int(km)} km",
        ha="center",
        va="top",
        fontsize=fontsize,
        color="black",
        zorder=9,
    )


def add_colorbar(fig, rect, breaks, colors, label, ticks, ticklabels=None) -> None:
    cax = fig.add_axes(rect)
    cmap = ListedColormap(colors)
    norm = BoundaryNorm(breaks, cmap.N)
    cbar = fig.colorbar(
        mpl.cm.ScalarMappable(norm=norm, cmap=cmap),
        cax=cax,
        orientation="horizontal",
        boundaries=breaks,
        ticks=ticks,
        spacing="uniform",
    )
    cbar.ax.tick_params(labelsize=8.6 * TEXT_SCALE, length=2.1, width=0.55, pad=1.0)
    if ticklabels is not None:
        cbar.ax.set_xticklabels(ticklabels)
    cbar.set_label(label, fontsize=8.9 * TEXT_SCALE, labelpad=1.0)
    cbar.outline.set_linewidth(0.55)


def plot_tile_panel(
    exporter,
    ax,
    iso3: str,
    panel_idx: int,
    kind: str,
    adm0,
    adm1,
    bounds,
    *,
    scale_km: float | None = None,
    tick_labelsize: float,
    scale_fontsize: float,
    mean_without_admin: bool = False,
) -> None:
    minx, miny, maxx, maxy = bounds
    pminx, pminy, pmaxx, pmaxy = exporter.pad_bounds(bounds)
    tile = exporter.read_tile(iso3, panel_idx, kind)
    ax.imshow(tile, extent=(minx, maxx, miny, maxy), origin="upper", interpolation="nearest", zorder=1)
    if not (kind == "mean" and mean_without_admin):
        adm1.boundary.plot(ax=ax, color="#8f8f8f", linewidth=0.56, alpha=0.98, zorder=3)
    adm0.boundary.plot(ax=ax, color="#171717", linewidth=1.05, alpha=0.95, zorder=4)
    ax.set_xlim(pminx, pmaxx)
    ax.set_ylim(pminy, pmaxy)
    ax.set_aspect("equal", adjustable="box")
    exporter.style_axis(ax, iso3)
    ax.tick_params(axis="both", labelsize=tick_labelsize, length=1.8, width=0.45, pad=1.1)
    if scale_km is not None:
        if iso3 == "ISR":
            add_top_left_scale_bar_low(exporter, ax, scale_km, scale_fontsize)
        else:
            exporter.add_scale_bar(ax, scale_km, "bottom-left", scale_fontsize)


def plot_tile_zoom(exporter, ax, iso3: str, zoom, adm0, adm1, bounds) -> None:
    minx, miny, maxx, maxy = bounds
    zminx, zminy, zmaxx, zmaxy = zoom
    tile = exporter.read_tile(iso3, 4, "diff")
    ax.imshow(tile, extent=(minx, maxx, miny, maxy), origin="upper", interpolation="nearest", zorder=1)
    adm1.boundary.plot(ax=ax, color="#8f8f8f", linewidth=0.54, alpha=0.98, zorder=3)
    adm0.boundary.plot(ax=ax, color="#171717", linewidth=1.00, alpha=0.95, zorder=4)
    ax.set_xlim(zminx, zmaxx)
    ax.set_ylim(zminy, zmaxy)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_linewidth(0.70)


def draw_figure(draw_red_lines: bool = False):
    if not TOP10_3KM.exists():
        raise FileNotFoundError(f"Missing 3 km top10 cluster polygons: {TOP10_3KM}")

    overlay = load_overlay_module()
    overlay.AEQD_TOP10_GEOJSON = TOP10_3KM
    overlay.TEXT_SCALE = TEXT_SCALE

    exporter = configure_exporter(overlay.load_exporter())
    cores = overlay.load_top10_core_polygons()
    irn_adm0, irn_adm1, irn_bounds = exporter.load_boundaries("IRN")
    isr_adm0, isr_adm1, isr_bounds = exporter.load_boundaries("ISR")
    refresh_tiles_if_needed(exporter, irn_adm1, irn_bounds, isr_adm1, isr_bounds)

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

    tick = 9.6 * TEXT_SCALE
    scale_font = 10.5 * TEXT_SCALE
    plot_tile_panel(exporter, axes["a"], "IRN", 1, "mean", irn_adm0, irn_adm1, irn_bounds, scale_km=500, tick_labelsize=tick, scale_fontsize=scale_font, mean_without_admin=True)
    plot_tile_panel(exporter, axes["b"], "IRN", 2, "mean", irn_adm0, irn_adm1, irn_bounds, tick_labelsize=tick, scale_fontsize=scale_font, mean_without_admin=True)
    plot_tile_panel(exporter, axes["c"], "IRN", 4, "diff", irn_adm0, irn_adm1, irn_bounds, tick_labelsize=tick, scale_fontsize=scale_font)
    plot_tile_panel(exporter, axes["d"], "ISR", 1, "mean", isr_adm0, isr_adm1, isr_bounds, scale_km=50, tick_labelsize=tick, scale_fontsize=scale_font, mean_without_admin=True)
    plot_tile_panel(exporter, axes["e"], "ISR", 2, "mean", isr_adm0, isr_adm1, isr_bounds, tick_labelsize=tick, scale_fontsize=scale_font, mean_without_admin=True)
    plot_tile_panel(exporter, axes["f"], "ISR", 4, "diff", isr_adm0, isr_adm1, isr_bounds, tick_labelsize=tick, scale_fontsize=scale_font)
    plot_tile_zoom(exporter, axes["g"], "IRN", exporter.IRAN_ZOOM, irn_adm0, irn_adm1, irn_bounds)
    plot_tile_zoom(exporter, axes["h"], "ISR", exporter.ISRAEL_ZOOM, isr_adm0, isr_adm1, isr_bounds)

    for key in ["b", "c", "e", "f"]:
        axes[key].tick_params(axis="y", labelleft=False)

    overlay.overlay_core_polygons(
        axes["c"],
        cores,
        "IRN",
        show_labels=True,
        label_offsets={2: (-0.090, 0.035), 9: (0.035, 0.035), 10: (0.020, -0.020)},
    )
    overlay.overlay_core_polygons(axes["f"], cores, "ISR", show_labels=True)
    overlay.overlay_core_polygons(axes["g"], cores, "IRN", zoom=True, show_labels=True)
    overlay.overlay_core_polygons(axes["h"], cores, "ISR", zoom=True, show_labels=True)

    exporter.add_zoom_box(axes["c"], exporter.IRAN_ZOOM)
    exporter.add_zoom_box(axes["f"], exporter.ISRAEL_ZOOM)

    if draw_red_lines:
        for src_ax, dst_ax, zoom, endpoints in [
            (axes["c"], axes["g"], exporter.IRAN_ZOOM, [((0, 3), (0.0, 1.0)), ((2, 3), (1.0, 1.0))]),
            (axes["f"], axes["h"], exporter.ISRAEL_ZOOM, [((0, 3), (0.0, 1.0)), ((2, 1), (0.0, 0.0))]),
        ]:
            z = zoom
            coords = [z[0], z[1], z[2], z[3]]
            for source_idx, target in endpoints:
                source = (coords[source_idx[0]], coords[source_idx[1]])
                fig.add_artist(ConnectionPatch(source, target, src_ax.transData, dst_ax.transAxes, color="#d00000", linewidth=0.8, zorder=45, clip_on=False))

    for label, key in zip(["(a)", "(b)", "(c)", "(g)", "(h)"], ["a", "b", "c", "g", "h"]):
        add_panel_label(axes[key], label)
    for label, key in zip(["(d)", "(e)", "(f)"], ["d", "e", "f"]):
        add_panel_label(axes[key], label, "upper-left")

    add_zoom_name(axes["g"], "Tehran", "bottom-right")
    add_zoom_name(axes["h"], "Tel Aviv\nDistrict", "top-left")

    add_colorbar(
        fig,
        [0.055, 0.118, 0.405, 0.016],
        MEAN_BREAKS,
        MEAN_COLORS,
        "NTL intensity (nW/cm$^2$/sr)",
        MEAN_BREAKS,
    )
    add_colorbar(
        fig,
        [0.530, 0.118, 0.405, 0.016],
        DIFF_BREAKS,
        DIFF_COLORS,
        "NTL intensity difference (nW/cm$^2$/sr)",
        DIFF_BREAKS,
        ["", "-10", "-5", "-3", "3", "5", "10", ""],
    )

    return fig, exporter


def main() -> None:
    fig, exporter = draw_figure(draw_red_lines=False)
    fig.savefig(OUT_NO_REDLINES, dpi=450, bbox_inches="tight", pad_inches=0.04)
    print(f"Wrote {OUT_NO_REDLINES}")
    exporter.plt.close(fig)


if __name__ == "__main__":
    main()
