from __future__ import annotations

import importlib.util
from pathlib import Path

import matplotlib as mpl
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd


HERE = Path(__file__).resolve().parent
BASE_SCRIPT = HERE / "make_figure4_aeqd_daily_curves.py"
DATA = (
    Path(r"D:\Research_vault\raw\writing\conflictntl\data")
    / "event_screening_geoboundaries_v2_qgis"
    / "buffer_ntl_aeqd3"
)
ATTACHMENTS = Path(r"D:\Research_vault\raw\writing\conflictntl\attachments")

DAILY_PANEL = DATA / "aeqd_3km_top10_daily_panel.csv"
TABLE1 = DATA / "aeqd_3km_top10_table1_complete.csv"


def load_base_module():
    spec = importlib.util.spec_from_file_location("figure4_base", BASE_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {BASE_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    daily = pd.read_csv(DAILY_PANEL, encoding="utf-8-sig")
    metrics = pd.read_csv(TABLE1, encoding="utf-8-sig")
    daily["date_dt"] = pd.to_datetime(daily["date"])
    daily["ANTL"] = pd.to_numeric(daily["ANTL"], errors="coerce")
    daily["event_count"] = pd.to_numeric(daily["event_count"], errors="coerce").fillna(0)
    metrics["n_event_points"] = pd.to_numeric(metrics["n_event_points"], errors="coerce")
    return daily, metrics


def select_cluster(metrics: pd.DataFrame, country: str, city: str) -> str:
    city_lower = city.lower()
    country_mask = metrics["country_mode"].astype(str).str.lower().eq(country.lower())
    city_mask = metrics["city_mode"].astype(str).str.lower().eq(city_lower)
    selected = metrics[country_mask & city_mask].sort_values("rank")
    if selected.empty:
        area_mask = metrics["area_name"].astype(str).str.lower().str.contains(city_lower, regex=False)
        selected = metrics[country_mask & area_mask].sort_values("rank")
    if selected.empty:
        raise RuntimeError(f"Cannot find 3 km cluster for {country} / {city}")
    return str(selected.iloc[0]["aeqd_cluster_id"])


def make_figure() -> list[Path]:
    base = load_base_module()
    base.configure_matplotlib()

    daily, metrics = load_data()
    selected = [
        {
            "cluster": select_cluster(metrics, "Iran", "Tehran"),
            "country": "Iran",
            "display_region": "Tehran–Karaj cluster",
            "color": "#0F4D92",
        },
        {
            "cluster": select_cluster(metrics, "Iran", "Shiraz"),
            "country": "Iran",
            "display_region": "Shiraz cluster",
            "color": "#D98D2B",
        },
        {
            "cluster": select_cluster(metrics, "Israel", "Kiryat Shmona"),
            "country": "Israel",
            "display_region": "Zefat–Akko cluster",
            "color": "#2A8C78",
        },
        {
            "cluster": select_cluster(metrics, "Israel", "Tel Aviv"),
            "country": "Israel",
            "display_region": "Tel Aviv–Petah Tiqwa cluster",
            "color": "#6F4A8E",
        },
    ]

    text_scale = 2.5
    panel_label_font = 10.2 * text_scale
    tick_font = 9.2 * text_scale
    x_tick_font = 8.6 * text_scale
    legend_font = 9.8 * text_scale
    axis_label_font = 10.5 * text_scale

    fig = plt.figure(figsize=(12.2, 15.15), dpi=600)
    gs = fig.add_gridspec(
        len(selected),
        1,
        left=0.15,
        right=0.91,
        top=0.90,
        bottom=0.12,
        hspace=0.38,
    )
    axes = [fig.add_subplot(gs[i, 0]) for i in range(len(selected))]

    for ax, item in zip(axes, selected):
        cid = item["cluster"]
        sub = daily[daily["aeqd_cluster_id"] == cid].sort_values("date_dt").copy()
        meta = metrics[metrics["aeqd_cluster_id"] == cid].iloc[0]
        sub["roll7"] = sub["ANTL"].rolling(7, center=True, min_periods=1).mean()

        base.add_period_background(ax)
        base.plot_gap_aware_line(ax, sub["date_dt"], sub["ANTL"], color="#9E9E9E", lw=0.65, alpha=0.55)
        base.plot_gap_aware_line(ax, sub["date_dt"], sub["roll7"], color=item["color"], lw=1.35)

        country = item["country"]
        label = f"{country} | {item['display_region']} (n={int(meta['n_event_points'])})"
        ax.text(
            0.0,
            1.035,
            label,
            transform=ax.transAxes,
            fontsize=panel_label_font,
            fontweight="bold",
            va="bottom",
            ha="left",
            color=base.COUNTRY_TEXT_COLORS.get(country, "#222222"),
            clip_on=False,
        )
        ax.set_xlim(pd.Timestamp(base.ANALYSIS_START), pd.Timestamp(base.ANALYSIS_END))
        ax.tick_params(labelsize=tick_font, length=2.5, width=0.6)

        yvals = pd.to_numeric(sub["ANTL"], errors="coerce")
        ymin = max(0, float(yvals.min(skipna=True)) * 0.82)
        ymax = float(yvals.max(skipna=True)) * 1.18
        if ymax > ymin:
            ax.set_ylim(ymin, ymax)

        ax2 = ax.twinx()
        ax2.bar(
            sub["date_dt"],
            sub["event_count"],
            width=0.85,
            color="#4D4D4D",
            alpha=0.16,
            linewidth=0,
            zorder=1,
        )
        event_axis_max = 30 if str(meta["city_mode"]) in {"Shiraz", "Tel Aviv"} else 60
        if float(sub["event_count"].max()) > event_axis_max:
            event_axis_max = int(((float(sub["event_count"].max()) + 29) // 30) * 30)
        ax2.set_ylim(0, event_axis_max)
        ax2.set_yticks([0, event_axis_max])
        ax2.tick_params(labelsize=tick_font, length=2.5, width=0.6)
        ax2.spines["top"].set_visible(False)

        if ax is not axes[-1]:
            ax.tick_params(labelbottom=False)
        else:
            ax.set_xticks([pd.Timestamp(x) for x in base.DATE_TICKS])
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
            ax.tick_params(axis="x", labelsize=x_tick_font, pad=3.0)

    handles = [
        mpl.lines.Line2D([0], [0], color="#9E9E9E", lw=0.8, alpha=0.65, label="ANTL"),
        mpl.lines.Line2D([0], [0], color="#222222", lw=1.35, label="7-day mean"),
        mpl.lines.Line2D([0], [0], color="#555555", lw=0.8, ls=(0, (2.2, 2.2)), alpha=0.7, label="missing-day"),
        mpl.patches.Patch(facecolor="#4D4D4D", alpha=0.16, label="event count"),
    ]
    fig.legend(
        handles=handles,
        loc="upper center",
        bbox_to_anchor=(0.535, 0.972),
        ncol=4,
        fontsize=legend_font,
        columnspacing=0.7,
        handletextpad=0.32,
        handlelength=1.2,
    )
    fig.text(0.065, 0.5, "ANTL (nW/cm\u00b2/sr)", va="center", ha="center", rotation="vertical", fontsize=axis_label_font, fontweight="semibold")
    fig.text(1.0, 0.5, "Event count", va="center", ha="center", rotation="vertical", fontsize=axis_label_font, fontweight="semibold")

    outputs = []
    stem = ATTACHMENTS / "v2_figure4_daily_curves_aeqd3km"
    for suffix in [".png", ".pdf", ".svg", ".tiff"]:
        path = stem.with_suffix(suffix)
        fig.savefig(path, bbox_inches="tight", dpi=600 if suffix in {".png", ".tiff"} else None)
        outputs.append(path)
    plt.close(fig)
    return outputs


def main() -> None:
    outputs = make_figure()
    for path in outputs:
        print(path)


if __name__ == "__main__":
    main()
