"""
Export standalone Figure 3 panel assets for manual PPT layout.

This is a presentation-asset exporter. By default it reuses cached GEE-rendered
NTL tiles. With --refresh-tiles, it re-renders those PNG tiles from GEE using the
style rules in this file. It does not modify the source analysis script.
"""
from __future__ import annotations

import argparse
import importlib.util
import os
from pathlib import Path

import ee
import geopandas as gpd
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.patches import Rectangle
from dotenv import load_dotenv
from PIL import Image


HERE = Path(__file__).resolve().parent
BASE_SCRIPT = HERE / "run_admin_scale_results.py"
DATA = Path(r"D:\Research_vault\raw\writing\conflictntl\data\event_screening_geoboundaries\admin_scale_v2")
GEO_BASE = Path(r"D:\Research_vault\raw\datasets\geoboundaries")
ATTACH = Path(r"D:\Research_vault\raw\writing\conflictntl\attachments")
OUT_DIR = ATTACH / "figure3_v2_panel_assets"
TILE_DIR = OUT_DIR / "_tiles"

MEAN_BREAKS = [0, 3, 10, 30, 80, 245]
MEAN_COLORS = ["#000000", "#333333", "#666666", "#b0b0b0", "#ffffff"]
DIFF_BREAKS = [-10, -5, -1, 1, 5, 10]
DIFF_COLORS = ["#253494", "#7fcdbb", "#fff2d8", "#fdae61", "#d73027"]

IRAN_ZOOM = (50.65, 35.18, 51.95, 36.08)
# Tel Aviv core zoom, matched to Tehran panel aspect ratio so h has the same visual width as g.
ISRAEL_ZOOM = (34.62, 31.94, 35.03, 32.225)


def fmt_lon(x: float, _pos=None) -> str:
    return f"{abs(x):.0f}°{'E' if x >= 0 else 'W'}"


def fmt_lat(y: float, _pos=None) -> str:
    return f"{abs(y):.0f}°{'N' if y >= 0 else 'S'}"


def degree_len_for_km(km: float, lat: float) -> float:
    import math

    return km / (111.32 * max(0.2, abs(math.cos(math.radians(lat)))))


def configure_matplotlib() -> None:
    mpl.rcParams.update({
        "font.family": "serif",
        "font.serif": ["Times New Roman", "Times", "DejaVu Serif", "serif"],
        "mathtext.fontset": "stix",
        "pdf.fonttype": 42,
        "svg.fonttype": "none",
        "axes.linewidth": 0.70,
    })


def load_boundaries(iso3: str) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame, tuple[float, float, float, float]]:
    adm0 = gpd.read_file(GEO_BASE / iso3 / f"osm_gee_geoboundaries_{iso3}_adm0.geojson").to_crs("EPSG:4326")
    adm1 = gpd.read_file(GEO_BASE / iso3 / f"osm_gee_geoboundaries_{iso3}_adm1.geojson").to_crs("EPSG:4326")
    geom = adm1.dissolve().geometry.iloc[0].buffer(0.001).buffer(-0.001).buffer(0.001)
    return adm0, adm1, geom.bounds


def load_base_module():
    spec = importlib.util.spec_from_file_location("admin_base", BASE_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {BASE_SCRIPT}")
    base = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(base)
    base.MEAN_ANTL_BREAKS = MEAN_BREAKS
    base.MEAN_ANTL_PALETTE = [c.lstrip("#") for c in MEAN_COLORS]
    base.DIFF_ANTL_BREAKS = DIFF_BREAKS
    base.DIFF_ANTL_PALETTE = [c.lstrip("#") for c in DIFF_COLORS]
    base.OUT_DIR = TILE_DIR
    return base


def init_gee() -> None:
    load_dotenv(Path(r"D:\NTL-GPT-Clone") / ".env")
    ee.Initialize(project=os.getenv("GEE_DEFAULT_PROJECT_ID"))


def refresh_tiles_for_country(
    base,
    iso3: str,
    adm1: gpd.GeoDataFrame,
    bounds: tuple[float, float, float, float],
) -> None:
    products = base._products_for_figure3()
    country_geom = adm1.dissolve().geometry.iloc[0].buffer(0.001).buffer(-0.001).buffer(0.001)
    region = ee.Geometry.Rectangle(bounds, proj="EPSG:4326", geodesic=False)
    country_ee = base.ee_geometry_from_shapely(country_geom.simplify(0.02, preserve_topology=True))
    dimensions = "900x620" if iso3 == "IRN" else "420x860"

    for panel_idx, kind in [(1, "mean"), (2, "mean"), (4, "diff")]:
        _label, image, _vis, product_kind = products[panel_idx - 1]
        if product_kind != kind:
            raise ValueError(f"Panel kind mismatch for {iso3} {panel_idx}: {product_kind} != {kind}")
        out = TILE_DIR / f"{iso3}_{panel_idx}_{kind}_asset_v2.png"
        rendered = base.figure3_visualize(image.clip(country_ee), kind)
        tile = base.download_rendered_rgba(rendered, region, out, dimensions=dimensions)
        if tile is None:
            raise RuntimeError(f"Failed to refresh {out}")
        print(f"refreshed tile: {out}")


def tile_path(iso3: str, panel_idx: int, kind: str) -> Path:
    path = TILE_DIR / f"{iso3}_{panel_idx}_{kind}_asset_v2.png"
    if not path.exists():
        raise FileNotFoundError(path)
    return path


def read_tile(iso3: str, panel_idx: int, kind: str) -> Image.Image:
    return Image.open(tile_path(iso3, panel_idx, kind)).convert("RGBA")


def cmap_norm(kind: str):
    if kind == "mean":
        cmap = ListedColormap(MEAN_COLORS)
        norm = BoundaryNorm(MEAN_BREAKS, cmap.N)
    else:
        cmap = ListedColormap(DIFF_COLORS)
        norm = BoundaryNorm(DIFF_BREAKS, cmap.N)
    cmap.set_bad((1, 1, 1, 0))
    return cmap, norm


def style_axis(ax: plt.Axes, iso3: str) -> None:
    ax.grid(False)
    ax.xaxis.set_major_formatter(mpl.ticker.FuncFormatter(fmt_lon))
    ax.yaxis.set_major_formatter(mpl.ticker.FuncFormatter(fmt_lat))
    if iso3 == "IRN":
        ax.xaxis.set_major_locator(mpl.ticker.MultipleLocator(5))
        ax.yaxis.set_major_locator(mpl.ticker.MultipleLocator(5))
        ax.tick_params(axis="x", labeltop=True, labelbottom=False, top=True, bottom=False)
    else:
        ax.xaxis.set_major_locator(mpl.ticker.MultipleLocator(1))
        ax.yaxis.set_major_locator(mpl.ticker.MultipleLocator(1))
        ax.tick_params(axis="x", labeltop=False, labelbottom=True, top=False, bottom=True)
    tick_labelsize = 4.7 if iso3 == "ISR" else 7.0
    ax.tick_params(axis="both", labelsize=tick_labelsize, length=2.0, width=0.45, pad=1.5)
    for spine in ax.spines.values():
        spine.set_linewidth(0.80)


def pad_bounds(bounds: tuple[float, float, float, float], frac: float = 0.035) -> tuple[float, float, float, float]:
    minx, miny, maxx, maxy = bounds
    dx = (maxx - minx) * frac
    dy = (maxy - miny) * frac
    return minx - dx, miny - dy, maxx + dx, maxy + dy


def add_scale_bar(ax: plt.Axes, km: float, position: str = "bottom-left", fontsize: float = 7.0) -> None:
    x0, x1 = ax.get_xlim()
    y0, y1 = ax.get_ylim()
    if position == "top-left":
        lat = y1 - 0.11 * (y1 - y0)
    else:
        lat = y0 + 0.12 * (y1 - y0)
    length = degree_len_for_km(km, lat)
    start = x0 + 0.10 * (x1 - x0)
    end = start + length
    ax.plot([start, end], [lat, lat], color="black", lw=1.35, solid_capstyle="butt", zorder=8)
    tick = 0.018 * (y1 - y0)
    ax.plot([start, start], [lat - tick, lat + tick], color="black", lw=0.85, zorder=8)
    ax.plot([end, end], [lat - tick, lat + tick], color="black", lw=0.85, zorder=8)
    label_offset = 0.055 * (y1 - y0)
    label_y = lat - label_offset if position == "top-left" else lat + label_offset
    label_va = "top" if position == "top-left" else "bottom"
    ax.text((start + end) / 2, label_y, f"{int(km)} km",
            ha="center", va=label_va, fontsize=fontsize, color="black")


def draw_panel(
    iso3: str,
    panel_label: str,
    panel_idx: int,
    kind: str,
    adm0: gpd.GeoDataFrame,
    adm1: gpd.GeoDataFrame,
    bounds: tuple[float, float, float, float],
    scale_km: float | None,
    out_name: str,
    figsize: tuple[float, float],
    scale_position: str = "bottom-left",
) -> None:
    minx, miny, maxx, maxy = bounds
    pminx, pminy, pmaxx, pmaxy = pad_bounds(bounds)
    fig, ax = plt.subplots(figsize=figsize, dpi=450)
    tile = read_tile(iso3, panel_idx, kind)
    ax.imshow(tile, extent=(minx, maxx, miny, maxy), origin="upper", interpolation="nearest", zorder=1)
    adm1.boundary.plot(ax=ax, color="#b8b8b8", linewidth=0.44, alpha=0.95, zorder=3)
    adm0.boundary.plot(ax=ax, color="#171717", linewidth=1.15, alpha=0.95, zorder=4)
    ax.set_xlim(pminx, pmaxx)
    ax.set_ylim(pminy, pmaxy)
    ax.set_aspect("equal", adjustable="box")
    style_axis(ax, iso3)
    if scale_km is not None:
        add_scale_bar(ax, scale_km, scale_position)
    ax.text(
        0.5,
        -0.16 if iso3 == "ISR" else -0.11,
        panel_label,
        transform=ax.transAxes,
        ha="center",
        va="top",
        fontsize=9.0,
        color="black",
    )
    fig.savefig(OUT_DIR / out_name, dpi=450, bbox_inches="tight", pad_inches=0.035)
    plt.close(fig)


def draw_zoom(
    iso3: str,
    panel_label: str,
    zoom: tuple[float, float, float, float],
    adm0: gpd.GeoDataFrame,
    adm1: gpd.GeoDataFrame,
    bounds: tuple[float, float, float, float],
    out_name: str,
) -> None:
    minx, miny, maxx, maxy = bounds
    zminx, zminy, zmaxx, zmaxy = zoom
    fig, ax = plt.subplots(figsize=(3.2, 2.2), dpi=450)
    tile = read_tile(iso3, 4, "diff")
    ax.imshow(tile, extent=(minx, maxx, miny, maxy), origin="upper", interpolation="nearest", zorder=1)
    adm1.boundary.plot(ax=ax, color="#b8b8b8", linewidth=0.44, alpha=0.95, zorder=3)
    adm0.boundary.plot(ax=ax, color="#171717", linewidth=1.10, alpha=0.95, zorder=4)
    ax.set_xlim(zminx, zmaxx)
    ax.set_ylim(zminy, zmaxy)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_linewidth(0.85)
    ax.text(0.5, -0.08, panel_label, transform=ax.transAxes, ha="center", va="top", fontsize=9.0, color="black")
    fig.savefig(OUT_DIR / out_name, dpi=450, bbox_inches="tight", pad_inches=0.035)
    plt.close(fig)


def draw_colorbar(
    out_name: str,
    breaks: list[float],
    colors: list[str],
    label: str,
    ticks: list[float] | None = None,
) -> None:
    fig = plt.figure(figsize=(3.6, 0.55), dpi=450)
    cax = fig.add_axes([0.06, 0.45, 0.88, 0.28])
    cmap = ListedColormap(colors)
    norm = BoundaryNorm(breaks, cmap.N)
    cbar = fig.colorbar(
        mpl.cm.ScalarMappable(norm=norm, cmap=cmap),
        cax=cax,
        orientation="horizontal",
        boundaries=breaks,
        ticks=breaks if ticks is None else ticks,
        spacing="uniform",
    )
    cbar.ax.tick_params(labelsize=7.0, length=2.0, width=0.45, pad=1.5)
    cbar.set_label(label, fontsize=7.4, labelpad=1.5)
    cbar.outline.set_linewidth(0.45)
    fig.savefig(OUT_DIR / out_name, dpi=450, bbox_inches="tight", pad_inches=0.02, transparent=True)
    plt.close(fig)


def plot_panel_on_ax(
    ax: plt.Axes,
    iso3: str,
    panel_idx: int,
    kind: str,
    adm0: gpd.GeoDataFrame,
    adm1: gpd.GeoDataFrame,
    bounds: tuple[float, float, float, float],
    scale_km: float | None = None,
    scale_position: str = "bottom-left",
    tick_labelsize: float = 6.5,
    scale_fontsize: float = 7.0,
) -> None:
    minx, miny, maxx, maxy = bounds
    pminx, pminy, pmaxx, pmaxy = pad_bounds(bounds)
    tile = read_tile(iso3, panel_idx, kind)
    ax.imshow(tile, extent=(minx, maxx, miny, maxy), origin="upper", interpolation="nearest", zorder=1)
    adm1.boundary.plot(ax=ax, color="#b8b8b8", linewidth=0.42, alpha=0.95, zorder=3)
    adm0.boundary.plot(ax=ax, color="#171717", linewidth=1.05, alpha=0.95, zorder=4)
    ax.set_xlim(pminx, pmaxx)
    ax.set_ylim(pminy, pmaxy)
    ax.set_aspect("equal", adjustable="box")
    style_axis(ax, iso3)
    ax.tick_params(axis="both", labelsize=tick_labelsize, length=1.8, width=0.45, pad=1.1)
    if scale_km is not None:
        add_scale_bar(ax, scale_km, scale_position, scale_fontsize)


def plot_zoom_on_ax(
    ax: plt.Axes,
    iso3: str,
    zoom: tuple[float, float, float, float],
    adm0: gpd.GeoDataFrame,
    adm1: gpd.GeoDataFrame,
    bounds: tuple[float, float, float, float],
) -> None:
    minx, miny, maxx, maxy = bounds
    zminx, zminy, zmaxx, zmaxy = zoom
    tile = read_tile(iso3, 4, "diff")
    ax.imshow(tile, extent=(minx, maxx, miny, maxy), origin="upper", interpolation="nearest", zorder=1)
    adm1.boundary.plot(ax=ax, color="#b8b8b8", linewidth=0.40, alpha=0.95, zorder=3)
    adm0.boundary.plot(ax=ax, color="#171717", linewidth=1.00, alpha=0.95, zorder=4)
    ax.set_xlim(zminx, zmaxx)
    ax.set_ylim(zminy, zmaxy)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_linewidth(0.70)


def add_zoom_box(ax: plt.Axes, zoom: tuple[float, float, float, float]) -> None:
    minx, miny, maxx, maxy = zoom
    ax.add_patch(
        Rectangle(
            (minx, miny),
            maxx - minx,
            maxy - miny,
            fill=False,
            edgecolor="black",
            linewidth=0.85,
            zorder=10,
        )
    )


def add_composite_colorbar(
    fig: plt.Figure,
    rect: list[float],
    breaks: list[float],
    colors: list[str],
    label: str,
    ticks: list[float] | None = None,
) -> None:
    cax = fig.add_axes(rect)
    cmap = ListedColormap(colors)
    norm = BoundaryNorm(breaks, cmap.N)
    cbar = fig.colorbar(
        mpl.cm.ScalarMappable(norm=norm, cmap=cmap),
        cax=cax,
        orientation="horizontal",
        boundaries=breaks,
        ticks=breaks if ticks is None else ticks,
        spacing="uniform",
    )
    cbar.ax.tick_params(labelsize=11.1, length=2.3, width=0.60, pad=1.1)
    cbar.set_label(label, fontsize=11.4, labelpad=1.2)
    cbar.outline.set_linewidth(0.55)


def draw_composite_figure(
    irn_adm0: gpd.GeoDataFrame,
    irn_adm1: gpd.GeoDataFrame,
    irn_bounds: tuple[float, float, float, float],
    isr_adm0: gpd.GeoDataFrame,
    isr_adm1: gpd.GeoDataFrame,
    isr_bounds: tuple[float, float, float, float],
    out_name: str = "figure3_v2_admin_ntl_composite.png",
    diff_ticks: list[float] | None = None,
) -> None:
    fig = plt.figure(figsize=(8.1, 7.05), dpi=450)

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

    plot_panel_on_ax(axes["a"], "IRN", 1, "mean", irn_adm0, irn_adm1, irn_bounds, 500,
                     tick_labelsize=9.6, scale_fontsize=10.5)
    plot_panel_on_ax(axes["b"], "IRN", 2, "mean", irn_adm0, irn_adm1, irn_bounds, None, tick_labelsize=9.6)
    plot_panel_on_ax(axes["c"], "IRN", 4, "diff", irn_adm0, irn_adm1, irn_bounds, None, tick_labelsize=9.6)
    plot_panel_on_ax(axes["d"], "ISR", 1, "mean", isr_adm0, isr_adm1, isr_bounds, 50, "top-left",
                     tick_labelsize=9.6, scale_fontsize=10.5)
    plot_panel_on_ax(axes["e"], "ISR", 2, "mean", isr_adm0, isr_adm1, isr_bounds, None, tick_labelsize=9.6)
    plot_panel_on_ax(axes["f"], "ISR", 4, "diff", isr_adm0, isr_adm1, isr_bounds, None, tick_labelsize=9.6)
    plot_zoom_on_ax(axes["g"], "IRN", IRAN_ZOOM, irn_adm0, irn_adm1, irn_bounds)
    plot_zoom_on_ax(axes["h"], "ISR", ISRAEL_ZOOM, isr_adm0, isr_adm1, isr_bounds)

    for key in ["b", "c", "e", "f"]:
        axes[key].tick_params(axis="y", labelleft=False)

    add_zoom_box(axes["c"], IRAN_ZOOM)
    add_zoom_box(axes["f"], ISRAEL_ZOOM)

    add_composite_colorbar(
        fig,
        [0.055, 0.118, 0.405, 0.024],
        MEAN_BREAKS,
        MEAN_COLORS,
        "NTL intensity (nW/cm$^2$/sr)",
    )
    add_composite_colorbar(
        fig,
        [0.530, 0.118, 0.405, 0.024],
        DIFF_BREAKS,
        DIFF_COLORS,
        "NTL intensity difference (nW/cm$^2$/sr)",
        ticks=[-5, -1, 1, 5] if diff_ticks is None else diff_ticks,
    )

    fig.savefig(OUT_DIR / out_name, dpi=450, bbox_inches="tight", pad_inches=0.04)
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--refresh-tiles",
        action="store_true",
        help="Re-render cached GEE PNG tiles before exporting panel assets.",
    )
    args = parser.parse_args()

    configure_matplotlib()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    TILE_DIR.mkdir(parents=True, exist_ok=True)

    irn_adm0, irn_adm1, irn_bounds = load_boundaries("IRN")
    isr_adm0, isr_adm1, isr_bounds = load_boundaries("ISR")

    if args.refresh_tiles:
        init_gee()
        base = load_base_module()
        refresh_tiles_for_country(base, "IRN", irn_adm1, irn_bounds)
        refresh_tiles_for_country(base, "ISR", isr_adm1, isr_bounds)

    draw_panel("IRN", "(a)", 1, "mean", irn_adm0, irn_adm1, irn_bounds, 500,
               "iran_prewar_period.png", (3.25, 2.30))
    draw_panel("IRN", "(b)", 2, "mean", irn_adm0, irn_adm1, irn_bounds, None,
               "iran_conflict_period.png", (3.25, 2.30))
    draw_panel("IRN", "(c)", 4, "diff", irn_adm0, irn_adm1, irn_bounds, None,
               "iran_conflict_minus_prewar.png", (3.25, 2.30))

    draw_panel("ISR", "(d)", 1, "mean", isr_adm0, isr_adm1, isr_bounds, 50,
               "israel_prewar_period.png", (1.75, 3.35), "top-left")
    draw_panel("ISR", "(e)", 2, "mean", isr_adm0, isr_adm1, isr_bounds, None,
               "israel_conflict_period.png", (1.75, 3.35))
    draw_panel("ISR", "(f)", 4, "diff", isr_adm0, isr_adm1, isr_bounds, None,
               "israel_conflict_minus_prewar.png", (1.75, 3.35))

    draw_zoom("IRN", "(g)", IRAN_ZOOM, irn_adm0, irn_adm1, irn_bounds,
              "iran_tehran_difference_zoom.png")
    draw_zoom("ISR", "(h)", ISRAEL_ZOOM, isr_adm0, isr_adm1, isr_bounds,
              "israel_tel_aviv_difference_zoom.png")

    draw_colorbar(
        "colorbar_mean_antl.png",
        MEAN_BREAKS,
        MEAN_COLORS,
        "NTL intensity (nW/cm$^2$/sr)",
    )
    draw_colorbar(
        "colorbar_antl_difference.png",
        DIFF_BREAKS,
        DIFF_COLORS,
        "NTL intensity difference (nW/cm$^2$/sr)",
        ticks=[-5, -1, 1, 5],
    )
    draw_composite_figure(irn_adm0, irn_adm1, irn_bounds, isr_adm0, isr_adm1, isr_bounds)

    print(f"Wrote assets to {OUT_DIR}")


if __name__ == "__main__":
    main()
