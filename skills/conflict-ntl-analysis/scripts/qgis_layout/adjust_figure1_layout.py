from pathlib import Path
import sys

QGIS_PYTHON_PATH = r"C:\Program Files\QGIS 3.38.3\apps\qgis\python"
if QGIS_PYTHON_PATH not in sys.path:
    sys.path.insert(0, QGIS_PYTHON_PATH)

from qgis.core import (
    QgsProject,
    QgsLayoutItemLegend,
    QgsLayoutItemPicture,
    QgsLayoutPoint,
    QgsUnitTypes,
    QgsLayoutExporter,
)

PROJECT_PATH = Path(r"D:\Research_vault\raw\code\NTL\scripts\conflictntl-letter\figure1_study_area_isw_event_map_qgis_legend_scale_v5.qgz")
PNG_PATH = Path(r"D:\Research_vault\raw\writing\conflictntl\attachments\figure1_study_area_isw_event_map_qgis.png")


def main():
    app = None
    try:
        from qgis.core import QgsApplication
        app = QgsApplication([], False)
        app.initQgis()
    except Exception:
        pass

    project = QgsProject.instance()
    project.clear()
    if not project.read(str(PROJECT_PATH)):
        raise RuntimeError(f"Failed to read project: {PROJECT_PATH}")

    layout_manager = project.layoutManager()
    layout = None
    for l in layout_manager.printLayouts():
        layout = l
        break

    if layout is None:
        raise RuntimeError("No print layout found in project")

    legend = None
    arrow = None
    for item in layout.items():
        if isinstance(item, QgsLayoutItemLegend):
            legend = item
        elif isinstance(item, QgsLayoutItemPicture):
            arrow = item

    if legend is None:
        raise RuntimeError("No legend found in layout")
    if arrow is None:
        raise RuntimeError("No north arrow found in layout")

    legend_pos = legend.positionWithUnits()
    new_legend_y = legend_pos.y() + 2
    legend.attemptMove(QgsLayoutPoint(legend_pos.x(), new_legend_y, QgsUnitTypes.LayoutMillimeters))
    print(f"Legend moved: y {legend_pos.y()} -> {new_legend_y}")

    arrow_pos = arrow.positionWithUnits()
    new_arrow_y = arrow_pos.y() - 2
    arrow.attemptMove(QgsLayoutPoint(arrow_pos.x(), new_arrow_y, QgsUnitTypes.LayoutMillimeters))
    print(f"North arrow moved: y {arrow_pos.y()} -> {new_arrow_y}")

    project.write(str(PROJECT_PATH))
    print(f"Project saved: {PROJECT_PATH}")

    exporter = QgsLayoutExporter(layout)
    image_settings = QgsLayoutExporter.ImageExportSettings()
    image_settings.dpi = 600
    if PNG_PATH.exists():
        PNG_PATH.unlink()
    result = exporter.exportToImage(str(PNG_PATH), image_settings)
    if result != QgsLayoutExporter.Success:
        raise RuntimeError(f"Export failed: {result}")
    print(f"PNG exported: {PNG_PATH}")

    if app:
        app.exitQgis()


if __name__ == "__main__":
    main()
