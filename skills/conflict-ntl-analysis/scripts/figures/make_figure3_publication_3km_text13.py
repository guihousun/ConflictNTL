"""
Export the manuscript Figure 3 PNG with 3 km top-10 core-impact polygons.

This script makes the final publication-style composite referenced by the TeX
manuscript and scales every text element by TEXT_SCALE.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import matplotlib as mpl
import matplotlib.patheffects as pe
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
OUT_MAIN = ATTACH / "Fig3_0518v4.png"
OUT_VERSIONED = ATTACH / "Fig3_0518v4_text13.png"
OUT_NO_REDLINES = ATTACH / "Fig3_0518v4_text13_no_redlines.png"


def load_overlay_module():
    spec = importlib.util.spec_from_file_location("figure3_overlay_base", OVERLAY_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {OVERLAY_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def add_panel_label(ax, label: str, loc: str = "upper-right") -> None:
    if loc == "upper-left-low":
        xy = (0.06, 0.80)
        ha = "left"
        va = "top"
        clip_on = True
    elif loc == "upper-left":
        xy = (0.06, 0.95)
        ha = "left"
        va = "top"
        clip_on = True
    else:
        xy = (0.94, 0.95)
        ha = "right"
        va = "top"
        clip_on = True
    ax.text(
        *xy,
        label,
        transform=ax.transAxes,
        ha=ha,
        va=va,
        fontsize=13.0 * TEXT_SCALE,
        color="black",
        zorder=50,
        clip_on=clip_on,
    )


def add_zoom_name(ax, text: str, loc: str) -> None:
    if loc == "bottom-right":
        xy = (0.95, 0.07)
        ha = "right"
        va = "bottom"
    elif loc == "bottom-left":
        xy = (0.04, 0.07)
        ha = "left"
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
        fontsize=8.6 * TEXT_SCALE,
        fontweight="bold",
        color="black",
        zorder=60,
        linespacing=0.82,
        bbox={"facecolor": "#c9c9c9", "edgecolor": "none", "alpha": 0.78, "pad": 0.65},
    )


def add_top_left_scale_bar_low(exporter, ax, km: float, fontsize: float) -> None:
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    lat = y1 - 0.18 * (y1 - y0)
    length = exporter.degree_len_for_km(km, lat)
    start = x0 + 0.035 * (x1 - x0)
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


def add_connector(fig, src_ax, dst_ax, start, end) -> None:
    con = ConnectionPatch(
        xyA=start,
        coordsA=src_ax.transData,
        xyB=end,
        coordsB=dst_ax.transAxes,
        color="#d00000",
        linewidth=0.8,
        zorder=45,
        clip_on=False,
    )
    fig.add_artist(con)


def add_colorbar(fig, rect, breaks, colors, label, ticks) -> None:
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
    cbar.set_label(label, fontsize=8.9 * TEXT_SCALE, labelpad=1.0)
    cbar.outline.set_linewidth(0.55)


def draw_figure(draw_red_lines: bool = True):
    if not TOP10_3KM.exists():
        raise FileNotFoundError(f"Missing 3 km top10 cluster polygons: {TOP10_3KM}")

    overlay = load_overlay_module()
    overlay.AEQD_TOP10_GEOJSON = TOP10_3KM
    overlay.TEXT_SCALE = TEXT_SCALE

    exporter = overlay.load_exporter()
    exporter.DIFF_BREAKS = [-1e9, -10, -3, 3, 10, 1e9]
    exporter.DIFF_COLORS = ["#253494", "#7fcdbb", "#fff2d8", "#fdae61", "#d73027"]
    exporter.TILE_DIR = exporter.OUT_DIR / "_tiles_diff_5class_10_3_3_10"
    exporter.ISRAEL_ZOOM = (34.62, 31.94, 35.03, 32.225)
    exporter.configure_matplotlib()

    cores = overlay.load_top10_core_polygons()
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

    tick = 9.6 * TEXT_SCALE
    scale_font = 10.5 * TEXT_SCALE
    exporter.plot_panel_on_ax(axes["a"], "IRN", 1, "mean", irn_adm0, irn_adm1, irn_bounds, 500, tick_labelsize=tick, scale_fontsize=scale_font)
    exporter.plot_panel_on_ax(axes["b"], "IRN", 2, "mean", irn_adm0, irn_adm1, irn_bounds, None, tick_labelsize=tick)
    exporter.plot_panel_on_ax(axes["c"], "IRN", 4, "diff", irn_adm0, irn_adm1, irn_bounds, None, tick_labelsize=tick)
    exporter.plot_panel_on_ax(axes["d"], "ISR", 1, "mean", isr_adm0, isr_adm1, isr_bounds, None, tick_labelsize=tick)
    exporter.plot_panel_on_ax(axes["e"], "ISR", 2, "mean", isr_adm0, isr_adm1, isr_bounds, None, tick_labelsize=tick)
    exporter.plot_panel_on_ax(axes["f"], "ISR", 4, "diff", isr_adm0, isr_adm1, isr_bounds, None, tick_labelsize=tick)
    exporter.plot_zoom_on_ax(axes["g"], "IRN", exporter.IRAN_ZOOM, irn_adm0, irn_adm1, irn_bounds)
    exporter.plot_zoom_on_ax(axes["h"], "ISR", exporter.ISRAEL_ZOOM, isr_adm0, isr_adm1, isr_bounds)

    for key in ["b", "c", "e", "f"]:
        axes[key].tick_params(axis="y", labelleft=False)

    overlay.overlay_core_polygons(
        axes["c"],
        cores,
        "IRN",
        show_labels=True,
        label_offsets={2: (-0.090, 0.035), 9: (0.035, 0.035), 10: (0.020, -0.020)},
        linewidth_scale=0.26,
    )
    overlay.overlay_core_polygons(axes["f"], cores, "ISR", show_labels=True)
    overlay.overlay_core_polygons(axes["g"], cores, "IRN", zoom=True, show_labels=True)
    overlay.overlay_core_polygons(axes["h"], cores, "ISR", zoom=True, show_labels=True)

    exporter.add_zoom_box(axes["c"], exporter.IRAN_ZOOM)
    exporter.add_zoom_box(axes["f"], exporter.ISRAEL_ZOOM)

    if draw_red_lines:
        zminx, zminy, zmaxx, zmaxy = exporter.IRAN_ZOOM
        add_connector(fig, axes["c"], axes["g"], (zminx, zmaxy), (0.0, 1.0))
        add_connector(fig, axes["c"], axes["g"], (zmaxx, zmaxy), (1.0, 1.0))
        zminx, zminy, zmaxx, zmaxy = exporter.ISRAEL_ZOOM
        add_connector(fig, axes["f"], axes["h"], (zminx, zmaxy), (0.0, 1.0))
        add_connector(fig, axes["f"], axes["h"], (zminx, zminy), (0.0, 0.0))

    for label, key in zip(["(a)", "(b)", "(c)", "(g)", "(h)"], ["a", "b", "c", "g", "h"]):
        add_panel_label(axes[key], label)
    add_top_left_scale_bar_low(exporter, axes["d"], 50, scale_font)
    for label, key in zip(["(d)", "(e)", "(f)"], ["d", "e", "f"]):
        add_panel_label(axes[key], label, "upper-left")

    add_zoom_name(axes["g"], "Tehran–Karaj\ncluster", "bottom-left")
    add_zoom_name(axes["h"], "Tel Aviv–Petah\nTiqwa cluster", "top-left")

    add_colorbar(
        fig,
        [0.055, 0.118, 0.405, 0.016],
        exporter.MEAN_BREAKS,
        exporter.MEAN_COLORS,
        "NTL intensity (nW/cm$^2$/sr)",
        exporter.MEAN_BREAKS,
    )
    add_colorbar(
        fig,
        [0.530, 0.118, 0.405, 0.016],
        exporter.DIFF_BREAKS,
        exporter.DIFF_COLORS,
        "NTL intensity difference (nW/cm$^2$/sr)",
        [-10, -3, 3, 10],
    )

    return fig, exporter


def main() -> None:
    fig, exporter = draw_figure(draw_red_lines=True)
    for out in [OUT_VERSIONED, OUT_MAIN]:
        fig.savefig(out, dpi=450, bbox_inches="tight", pad_inches=0.04)
        print(f"Wrote {out}")
    exporter.plt.close(fig)

    fig, exporter = draw_figure(draw_red_lines=False)
    fig.savefig(OUT_NO_REDLINES, dpi=450, bbox_inches="tight", pad_inches=0.04)
    print(f"Wrote {OUT_NO_REDLINES}")
    exporter.plt.close(fig)


if __name__ == "__main__":
    main()
