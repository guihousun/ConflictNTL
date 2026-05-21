from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import pandas as pd


DATA = (
    Path(r"D:\Research_vault\raw\writing\conflictntl\data")
    / "event_screening_geoboundaries_v2_qgis"
    / "buffer_ntl_aeqd5"
)
ATTACHMENTS = Path(r"D:\Research_vault\raw\writing\conflictntl\attachments")

DAILY_PANEL = DATA / "aeqd_5km_top10_daily_panel.csv"
TABLE1 = DATA / "aeqd_5km_top10_table1_complete.csv"

ANALYSIS_START = "2026-02-13"
PREWAR_END = "2026-02-26"
CONFLICT_START = "2026-02-27"
CONFLICT_END = "2026-04-07"
CEASEFIRE_START = "2026-04-08"
ANALYSIS_END = "2026-04-21"
DATE_TICKS = [ANALYSIS_START, CONFLICT_START, CONFLICT_END, ANALYSIS_END]

COUNTRY_TEXT_COLORS = {
    "Israel": "#1F5F9F",
    "Iran": "#9A3B32",
}

SELECTED = [
    {"cluster": "AEQD5_002", "color": "#0F4D92"},  # Tehran
    {"cluster": "AEQD5_005", "color": "#D98D2B"},  # Shiraz
    {"cluster": "AEQD5_001", "color": "#2A8C78"},  # Kiryat Shmona
    {"cluster": "AEQD5_004", "color": "#6F4A8E"},  # Tel Aviv
]


def configure_matplotlib() -> None:
    plt.rcParams["font.family"] = "serif"
    plt.rcParams["font.serif"] = ["Times New Roman", "Times", "Nimbus Roman", "Liberation Serif", "DejaVu Serif"]
    plt.rcParams["mathtext.fontset"] = "stix"
    plt.rcParams["svg.fonttype"] = "none"
    plt.rcParams["pdf.fonttype"] = 42
    plt.rcParams["font.size"] = 10
    plt.rcParams["axes.linewidth"] = 0.75
    plt.rcParams["axes.spines.right"] = False
    plt.rcParams["axes.spines.top"] = False
    plt.rcParams["legend.frameon"] = False


def place_from_area_name(area_name: str) -> tuple[str, str]:
    text = str(area_name)
    if " / " not in text:
        return "", text
    country, rest = text.split(" / ", 1)
    place = rest
    for suffix in [
        " military-base event core",
        " industrial/energy event core",
        " rocket/missile event core",
        " airbase event core",
        " event core",
    ]:
        place = place.replace(suffix, "")
    return country.strip(), place.strip()


def label_from_meta(meta: pd.Series) -> tuple[str, str]:
    country, place = place_from_area_name(str(meta["area_name"]))
    n = int(meta["n_event_points"])
    if country:
        return country, f"{country} | {place} (n={n})"
    return "", f"{place} (n={n})"


def add_period_background(ax: plt.Axes) -> None:
    for start, end, color in [
        (ANALYSIS_START, PREWAR_END, "#e8f1ff"),
        (CONFLICT_START, CONFLICT_END, "#ffe5e5"),
        (CEASEFIRE_START, ANALYSIS_END, "#e8f5e9"),
    ]:
        ax.axvspan(pd.Timestamp(start), pd.Timestamp(end), color=color, alpha=0.72, lw=0, zorder=0)
    ax.axvline(pd.Timestamp(CONFLICT_START), color="#555555", lw=0.55, ls="--", alpha=0.82)
    ax.axvline(pd.Timestamp(CEASEFIRE_START), color="#555555", lw=0.55, ls="--", alpha=0.82)


def plot_gap_aware_line(
    ax: plt.Axes,
    dates: pd.Series,
    values: pd.Series,
    *,
    color: str,
    lw: float,
    alpha: float = 1.0,
    solid_zorder: int = 3,
    gap_zorder: int = 2,
) -> None:
    series = pd.DataFrame({"date": pd.to_datetime(dates), "value": pd.to_numeric(values, errors="coerce")})
    series = series.dropna(subset=["date", "value"]).sort_values("date").reset_index(drop=True)
    if series.empty:
        return

    seg_dates = [series.loc[0, "date"]]
    seg_values = [series.loc[0, "value"]]
    for idx in range(1, len(series)):
        prev_date = series.loc[idx - 1, "date"]
        curr_date = series.loc[idx, "date"]
        prev_value = series.loc[idx - 1, "value"]
        curr_value = series.loc[idx, "value"]
        gap_days = int((curr_date - prev_date).days)
        if gap_days <= 1:
            seg_dates.append(curr_date)
            seg_values.append(curr_value)
            continue
        if len(seg_dates) > 1:
            ax.plot(seg_dates, seg_values, color=color, lw=lw, alpha=alpha, zorder=solid_zorder)
        ax.plot(
            [prev_date, curr_date],
            [prev_value, curr_value],
            color=color,
            lw=lw,
            alpha=alpha,
            ls=(0, (2.2, 2.2)),
            zorder=gap_zorder,
        )
        seg_dates = [curr_date]
        seg_values = [curr_value]
    if len(seg_dates) > 1:
        ax.plot(seg_dates, seg_values, color=color, lw=lw, alpha=alpha, zorder=solid_zorder)


def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    daily = pd.read_csv(DAILY_PANEL, encoding="utf-8-sig")
    metrics = pd.read_csv(TABLE1, encoding="utf-8-sig")
    daily["date_dt"] = pd.to_datetime(daily["date"])
    daily["ANTL"] = pd.to_numeric(daily["ANTL"], errors="coerce")
    daily["event_count"] = pd.to_numeric(daily["event_count"], errors="coerce").fillna(0)
    daily["valid_pixel_ratio"] = pd.to_numeric(daily["valid_pixel_ratio"], errors="coerce")
    metrics["n_event_points"] = pd.to_numeric(metrics["n_event_points"], errors="coerce")
    return daily, metrics


def make_figure() -> list[Path]:
    configure_matplotlib()
    text_scale = 2.5
    panel_label_font = 10.2 * text_scale
    tick_font = 9.2 * text_scale
    x_tick_font = 8.6 * text_scale
    legend_font = 9.8 * text_scale
    axis_label_font = 10.5 * text_scale

    daily, metrics = load_data()

    fig = plt.figure(figsize=(12.2, 15.15), dpi=600)
    gs = fig.add_gridspec(
        len(SELECTED),
        1,
        left=0.15,
        right=0.91,
        top=0.90,
        bottom=0.12,
        hspace=0.38,
    )
    axes = [fig.add_subplot(gs[i, 0]) for i in range(len(SELECTED))]

    selected_ids = [item["cluster"] for item in SELECTED]
    scoped = daily[daily["aeqd_cluster_id"].isin(selected_ids)].copy()
    event_ymax = max(1.0, float(scoped["event_count"].max()))

    for ax, item in zip(axes, SELECTED):
        cid = item["cluster"]
        sub = daily[daily["aeqd_cluster_id"] == cid].sort_values("date_dt").copy()
        meta = metrics[metrics["aeqd_cluster_id"] == cid].iloc[0]
        sub["roll7"] = sub["ANTL"].rolling(7, center=True, min_periods=1).mean()

        add_period_background(ax)
        plot_gap_aware_line(ax, sub["date_dt"], sub["ANTL"], color="#9E9E9E", lw=0.65, alpha=0.55)
        plot_gap_aware_line(ax, sub["date_dt"], sub["roll7"], color=item["color"], lw=1.35)

        country, label = label_from_meta(meta)
        ax.text(
            0.0,
            1.035,
            label,
            transform=ax.transAxes,
            fontsize=panel_label_font,
            fontweight="bold",
            va="bottom",
            ha="left",
            color=COUNTRY_TEXT_COLORS.get(country, "#222222"),
            clip_on=False,
        )
        ax.set_xlim(pd.Timestamp(ANALYSIS_START), pd.Timestamp(ANALYSIS_END))
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
        event_axis_max = 30 if cid in {"AEQD5_005", "AEQD5_004"} else 60
        ax2.set_ylim(0, event_axis_max)
        ax2.set_yticks([0, event_axis_max])
        ax2.tick_params(labelsize=tick_font, length=2.5, width=0.6)
        ax2.spines["top"].set_visible(False)

        if ax is not axes[-1]:
            ax.tick_params(labelbottom=False)
        else:
            ax.set_xticks([pd.Timestamp(x) for x in DATE_TICKS])
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

    fig.text(
        0.065,
        0.5,
        "ANTL (nW/cm\u00b2/sr)",
        va="center",
        ha="center",
        rotation="vertical",
        fontsize=axis_label_font,
        fontweight="semibold",
    )
    fig.text(
        1.0,
        0.5,
        "Event count",
        va="center",
        ha="center",
        rotation="vertical",
        fontsize=axis_label_font,
        fontweight="semibold",
    )

    outputs = []
    for stem_name in ["v2_figure4_daily_curves_aeqd", "v2_figure4_daily_curves"]:
        stem = ATTACHMENTS / stem_name
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
