from __future__ import annotations

import importlib.util
from pathlib import Path


HERE = Path(__file__).resolve().parent
BASE_SCRIPT = HERE / "export_figure3_v2_admin_ntl_top10_core_overlay.py"
TOP10_3KM = (
    Path(r"D:\Research_vault\raw\writing\conflictntl\data")
    / "event_screening_geoboundaries_v2_qgis"
    / "buffer_ntl_aeqd3"
    / "aeqd_3km_top10_clusters.geojson"
)


def load_base_module():
    spec = importlib.util.spec_from_file_location("figure3_overlay_base", BASE_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {BASE_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    if not TOP10_3KM.exists():
        raise FileNotFoundError(f"Missing 3 km top10 cluster polygons: {TOP10_3KM}")

    overlay = load_base_module()
    overlay.AEQD_TOP10_GEOJSON = TOP10_3KM

    exporter = overlay.load_exporter()
    exporter.DIFF_BREAKS = [-1e9, -10, -3, 3, 10, 1e9]
    exporter.DIFF_COLORS = ["#253494", "#7fcdbb", "#fff2d8", "#fdae61", "#d73027"]
    exporter.TILE_DIR = exporter.OUT_DIR / "_tiles_diff_5class_10_3_3_10"
    exporter.ISRAEL_ZOOM = (34.62, 31.94, 35.03, 32.225)
    exporter.configure_matplotlib()

    cores = overlay.load_top10_core_polygons()
    overlay.draw_overlay_composite(
        exporter,
        cores,
        show_labels=True,
        out_name="figure3_v2_admin_ntl_composite_diff_5class_10_3_3_10_aeqd3km_top10_core_polygons_ranked.png",
    )
    overlay.draw_overlay_composite(
        exporter,
        cores,
        show_labels=False,
        out_name="figure3_v2_admin_ntl_composite_diff_5class_10_3_3_10_aeqd3km_top10_core_polygons.png",
    )


if __name__ == "__main__":
    main()
