from __future__ import annotations

import csv
import os
from datetime import date
from pathlib import Path

from qgis.PyQt.QtCore import QVariant
from qgis.PyQt.QtGui import QColor, QFont
from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsFeature,
    QgsField,
    QgsGeometry,
    QgsLayoutExporter,
    QgsLayoutItemLegend,
    QgsLayoutItemLabel,
    QgsLayoutItemMap,
    QgsLayoutItemMapGrid,
    QgsLayoutItemPicture,
    QgsLayoutItemScaleBar,
    QgsLayoutItemShape,
    QgsLayoutPoint,
    QgsLayoutSize,
    QgsLineSymbol,
    QgsMarkerSymbol,
    QgsPalLayerSettings,
    QgsPrintLayout,
    QgsProject,
    QgsRasterLayer,
    QgsRectangle,
    QgsScaleBarSettings,
    QgsTextBufferSettings,
    QgsTextFormat,
    QgsUnitTypes,
    QgsVectorLayer,
    QgsVectorFileWriter,
    QgsVectorLayerSimpleLabeling,
    QgsWkbTypes,
    Qgis,
)


ROOT = Path(r"D:\Research_vault")
THREAD = Path(r"D:\NTL-GPT-Clone\user_data\conflictntl-us-israel-iran-fullcase")
INPUT_CSV = THREAD / "inputs" / "ISW_storymap_events_2026-02-27_2026-04-27.csv"
GEOB_ADMIN_DIR = ROOT / "raw" / "datasets" / "geoboundaries"
ADMIN_FILES = {
    "ADM0": [
        GEOB_ADMIN_DIR / "IRN" / "osm_gee_geoboundaries_IRN_adm0.geojson",
        GEOB_ADMIN_DIR / "ISR" / "osm_gee_geoboundaries_ISR_adm0.geojson",
    ],
    "ADM1": [
        GEOB_ADMIN_DIR / "IRN" / "osm_gee_geoboundaries_IRN_adm1.geojson",
        GEOB_ADMIN_DIR / "ISR" / "osm_gee_geoboundaries_ISR_adm1.geojson",
    ],
    "ADM2": [
        GEOB_ADMIN_DIR / "IRN" / "osm_gee_geoboundaries_IRN_adm2.geojson",
        GEOB_ADMIN_DIR / "ISR" / "osm_gee_geoboundaries_ISR_adm2.geojson",
    ],
}
ATTACH_DIR = ROOT / "raw" / "writing" / "conflictntl" / "attachments"
OUT_DIR = ROOT / "raw" / "code" / "NTL" / "scripts" / "conflictntl-letter"
NORTH_ARROW = ATTACH_DIR / "north-arrow-svgrepo-com.svg"
QGIS_NORTH_ARROW = Path(r"C:\Program Files\QGIS 3.38.3\apps\qgis\svg\arrows\NorthArrow_04.svg")
LAYER_GPKG = OUT_DIR / "figure1_study_area_isw_event_map_qgis_osm_admin_v4_layers.gpkg"

EVENT_START = date.fromisoformat("2026-02-27")
EVENT_END = date.fromisoformat("2026-04-21")
EXTENT_PADDING_DEG = 0.25
WEB_CRS = QgsCoordinateReferenceSystem("EPSG:3857")
GEO_CRS = QgsCoordinateReferenceSystem("EPSG:4326")


def safe_layer_name(name: str) -> str:
    value = "".join(ch.lower() if ch.isalnum() else "_" for ch in name)
    return "_".join(part for part in value.split("_") if part)


def materialize_vector_layer(project: QgsProject, layer: QgsVectorLayer) -> QgsVectorLayer:
    gpkg_layer_name = safe_layer_name(layer.name())
    options = QgsVectorFileWriter.SaveVectorOptions()
    options.driverName = "GPKG"
    options.layerName = gpkg_layer_name
    options.actionOnExistingFile = (
        QgsVectorFileWriter.CreateOrOverwriteLayer if LAYER_GPKG.exists() else QgsVectorFileWriter.CreateOrOverwriteFile
    )
    result = QgsVectorFileWriter.writeAsVectorFormatV3(layer, str(LAYER_GPKG), project.transformContext(), options)
    error = result[0] if isinstance(result, tuple) else result
    if error != QgsVectorFileWriter.NoError:
        raise RuntimeError(f"Failed to write {layer.name()} to {LAYER_GPKG}: {result}")

    persistent = QgsVectorLayer(f"{LAYER_GPKG}|layername={gpkg_layer_name}", layer.name(), "ogr")
    if not persistent.isValid():
        raise RuntimeError(f"Failed to reload persistent layer: {layer.name()} from {LAYER_GPKG}")
    if layer.renderer():
        persistent.setRenderer(layer.renderer().clone())
    if layer.labelsEnabled() and layer.labeling():
        persistent.setLabeling(layer.labeling().clone())
        persistent.setLabelsEnabled(True)
    return persistent


def classify_axis_actor(actor: str) -> str:
    a = actor.lower()
    if "hezbollah" in a:
        return "Hezbollah"
    if "houth" in a:
        return "Houthis"
    if "militia" in a or "militas" in a or "saraya" in a:
        return "Iraqi militias"
    if "iran" in a:
        return "Iran"
    return "Iran"


def classify_combined_event(event_type: str) -> str:
    e = event_type.lower()
    if "confirmed airstrike" in e:
        return "Confirmed airstrike"
    if "reported airstrike" in e:
        return "Reported airstrike"
    if "explosion" in e:
        return "Explosion report"
    return "Reported airstrike"


def parse_event_date(row: dict[str, str]) -> date | None:
    for key in ("date", "event_date_utc", "post_date_utc", "publication_date_utc"):
        value = (row.get(key) or "").strip()
        if not value:
            continue
        try:
            return date.fromisoformat(value[:10])
        except ValueError:
            continue
    return None


def read_events() -> dict[str, list[tuple[float, float]]]:
    groups = {
        "Iran-axis strikes": [],
        "US/Israeli strikes": [],
    }
    lon_min, lon_max, lat_min, lat_max = study_extent()
    with INPUT_CSV.open("r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            try:
                lon = float(row.get("longitude") or "")
                lat = float(row.get("latitude") or "")
            except ValueError:
                continue
            if not (lon_min <= lon <= lon_max and lat_min <= lat <= lat_max):
                continue
            event_date = parse_event_date(row)
            if event_date is None or event_date < EVENT_START or event_date > EVENT_END:
                continue
            family = row.get("event_family") or ""
            if family == "iran_axis_retaliatory_strike":
                group = "Iran-axis strikes"
            elif family == "us_israel_combined_force_strike":
                group = "US/Israeli strikes"
            else:
                continue
            if group in groups:
                groups[group].append((lon, lat))
    return groups


def make_point_layer(name: str, points: list[tuple[float, float]], symbol_name: str, fill: str, outline: str) -> QgsVectorLayer:
    layer = QgsVectorLayer("Point?crs=EPSG:4326", name, "memory")
    provider = layer.dataProvider()
    provider.addAttributes([QgsField("name", QVariant.String)])
    layer.updateFields()
    features = []
    for lon, lat in points:
        feat = QgsFeature(layer.fields())
        feat.setAttributes([name])
        feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(lon, lat)))
        features.append(feat)
    provider.addFeatures(features)
    layer.updateExtents()
    symbol = QgsMarkerSymbol.createSimple(
        {
            "name": symbol_name,
            "color": fill,
            "outline_color": outline,
            "outline_width": "0.32",
            "outline_width_unit": "MM",
            "size": "1.85",
            "size_unit": "MM",
        }
    )
    symbol.setOpacity(0.78)
    layer.setRenderer(QgsSingleSymbolRenderer(symbol))
    return layer


def make_boundary_line_layer(name: str, admin_level: str, outline: str, width_mm: float, opacity: float) -> QgsVectorLayer:
    layer = QgsVectorLayer("MultiLineString?crs=EPSG:4326", name, "memory")
    provider = layer.dataProvider()
    features = []
    for path in ADMIN_FILES[admin_level]:
        source = QgsVectorLayer(str(path), f"{path.stem} source", "ogr")
        if not source.isValid():
            raise RuntimeError(f"Failed to load boundary layer: {path}")
        for source_feat in source.getFeatures():
            boundary = source_feat.geometry().convertToType(Qgis.GeometryType.Line, True)
            if boundary.isEmpty():
                continue
            feat = QgsFeature(layer.fields())
            feat.setGeometry(boundary)
            features.append(feat)
    provider.addFeatures(features)
    layer.updateExtents()
    symbol = QgsLineSymbol.createSimple(
        {
            "line_color": outline,
            "line_width": f"{width_mm}",
            "line_width_unit": "MM",
            "capstyle": "round",
            "joinstyle": "round",
        }
    )
    symbol.setOpacity(opacity)
    layer.setRenderer(QgsSingleSymbolRenderer(symbol))
    return layer


def make_country_outline_layer() -> QgsVectorLayer:
    layer = QgsVectorLayer("MultiLineString?crs=EPSG:4326", "Study area", "memory")
    provider = layer.dataProvider()
    provider.addAttributes([QgsField("country_iso3", QVariant.String)])
    layer.updateFields()
    features = []
    for path in ADMIN_FILES["ADM0"]:
        source = QgsVectorLayer(str(path), f"{path.stem} source", "ogr")
        if not source.isValid():
            raise RuntimeError(f"Failed to load ADM0 boundary layer: {path}")
        field_names = source.fields().names()
        for feat in source.getFeatures():
            out = QgsFeature(layer.fields())
            out.setAttributes([feat["iso3"] if "iso3" in field_names else path.parent.name])
            out.setGeometry(feat.geometry().convertToType(Qgis.GeometryType.Line, True))
            features.append(out)
    provider.addFeatures(features)
    layer.updateExtents()
    symbol = QgsLineSymbol.createSimple(
        {
            "line_color": "#d7191c",
            "line_width": "0.70",
            "line_width_unit": "MM",
            "joinstyle": "round",
            "capstyle": "round",
        }
    )
    layer.setRenderer(QgsSingleSymbolRenderer(symbol))
    return layer


def make_city_label_layer() -> QgsVectorLayer:
    cities = [
        ("Tehran", 51.389, 35.689),
        ("Tabriz", 46.291, 38.096),
        ("Shiraz", 52.583, 29.592),
        ("Ahvaz", 48.670, 31.319),
        ("Haifa", 34.989, 32.794),
        ("Tel Aviv", 34.781, 32.085),
    ]
    layer = QgsVectorLayer("Point?crs=EPSG:4326", "Key city labels", "memory")
    provider = layer.dataProvider()
    provider.addAttributes([QgsField("name", QVariant.String)])
    layer.updateFields()
    features = []
    for name, lon, lat in cities:
        feat = QgsFeature(layer.fields())
        feat.setAttributes([name])
        feat.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(lon, lat)))
        features.append(feat)
    provider.addFeatures(features)
    layer.updateExtents()
    symbol = QgsMarkerSymbol.createSimple({"name": "circle", "color": "0,0,0,0", "outline_color": "0,0,0,0", "size": "0"})
    layer.setRenderer(QgsSingleSymbolRenderer(symbol))

    fmt = QgsTextFormat()
    fmt.setFont(QFont("Arial", 5))
    fmt.setSize(5)
    fmt.setColor(QColor("#1f1f1f"))
    buffer = QgsTextBufferSettings()
    buffer.setEnabled(True)
    buffer.setColor(QColor(255, 255, 255, 210))
    buffer.setSize(0.45)
    fmt.setBuffer(buffer)
    settings = QgsPalLayerSettings()
    settings.fieldName = "name"
    settings.placement = QgsPalLayerSettings.AroundPoint
    settings.dist = 0.9
    settings.setFormat(fmt)
    layer.setLabeling(QgsVectorLayerSimpleLabeling(settings))
    layer.setLabelsEnabled(True)
    return layer


def study_extent() -> tuple[float, float, float, float]:
    geoms = []
    for path in ADMIN_FILES["ADM0"]:
        source = QgsVectorLayer(str(path), f"{path.stem} extent source", "ogr")
        if not source.isValid():
            raise RuntimeError(f"Failed to load extent boundary layer: {path}")
        for feat in source.getFeatures():
            geoms.append(QgsGeometry(feat.geometry()))
    if not geoms:
        raise RuntimeError("No Iran/Israel ADM1 geometries found for study extent.")
    bounds = QgsGeometry.unaryUnion(geoms).boundingBox()
    return (
        bounds.xMinimum() - EXTENT_PADDING_DEG,
        bounds.xMaximum() + EXTENT_PADDING_DEG,
        bounds.yMinimum() - EXTENT_PADDING_DEG,
        bounds.yMaximum() + EXTENT_PADDING_DEG,
    )


def web_extent(project: QgsProject) -> QgsRectangle:
    transform = QgsCoordinateTransform(GEO_CRS, WEB_CRS, project)
    lon_min, lon_max, lat_min, lat_max = study_extent()
    p1 = transform.transform(lon_min, lat_min)
    p2 = transform.transform(lon_max, lat_max)
    return QgsRectangle(p1.x(), p1.y(), p2.x(), p2.y())


def add_grid(map_item: QgsLayoutItemMap) -> None:
    grid = QgsLayoutItemMapGrid("4 degree geographic grid", map_item)
    grid.setEnabled(True)
    grid.setCrs(GEO_CRS)
    grid.setStyle(QgsLayoutItemMapGrid.Solid)
    grid.setIntervalX(5)
    grid.setIntervalY(5)
    grid.setGridLineColor(QColor(75, 75, 75, 78))
    grid.setGridLineWidth(0.09)
    grid.setAnnotationEnabled(True)
    grid.setAnnotationFormat(QgsLayoutItemMapGrid.DecimalWithSuffix)
    grid.setAnnotationPrecision(0)
    grid.setAnnotationFont(QFont("Arial", 5))
    grid.setAnnotationFontColor(QColor("#222222"))
    grid.setAnnotationFrameDistance(1.4)
    grid.setAnnotationDisplay(QgsLayoutItemMapGrid.ShowAll, QgsLayoutItemMapGrid.Top)
    grid.setAnnotationDisplay(QgsLayoutItemMapGrid.ShowAll, QgsLayoutItemMapGrid.Bottom)
    grid.setAnnotationDisplay(QgsLayoutItemMapGrid.ShowAll, QgsLayoutItemMapGrid.Left)
    grid.setAnnotationDisplay(QgsLayoutItemMapGrid.ShowAll, QgsLayoutItemMapGrid.Right)
    grid.setAnnotationDirection(QgsLayoutItemMapGrid.Horizontal, QgsLayoutItemMapGrid.Top)
    grid.setAnnotationDirection(QgsLayoutItemMapGrid.Horizontal, QgsLayoutItemMapGrid.Bottom)
    grid.setAnnotationDirection(QgsLayoutItemMapGrid.Vertical, QgsLayoutItemMapGrid.Left)
    grid.setAnnotationDirection(QgsLayoutItemMapGrid.Vertical, QgsLayoutItemMapGrid.Right)
    map_item.grids().addGrid(grid)


def add_legend(layout: QgsPrintLayout, map_item: QgsLayoutItemMap, keep_names: list[str]) -> None:
    legend = QgsLayoutItemLegend(layout)
    legend.setTitle("")
    legend.setLinkedMap(map_item)
    legend.setAutoUpdateModel(False)
    root = legend.model().rootGroup()
    for child in list(root.children()):
        if child.name() not in keep_names:
            root.removeChildNode(child)
    legend.setColumnCount(2)
    legend.setSplitLayer(False)
    legend.setSymbolWidth(3.6)
    legend.setSymbolHeight(2.8)
    legend.setBoxSpace(0.65)
    legend.setColumnSpace(3.2)
    legend.setBackgroundEnabled(True)
    legend.setBackgroundColor(QColor(255, 255, 255, 218))
    legend.setFrameEnabled(True)
    legend.setFrameStrokeColor(QColor(40, 40, 40, 120))
    legend.setFrameStrokeWidth(QgsLayoutMeasurement(0.18, QgsUnitTypes.LayoutMillimeters))
    font = QFont("Arial", 8)
    for style in (QgsLegendStyle.Title, QgsLegendStyle.Group, QgsLegendStyle.Subgroup, QgsLegendStyle.SymbolLabel):
        legend.rstyle(style).setFont(font)
    for style in (QgsLegendStyle.Title, QgsLegendStyle.Group, QgsLegendStyle.Subgroup, QgsLegendStyle.SymbolLabel):
        for side in (QgsLegendStyle.Top, QgsLegendStyle.Bottom, QgsLegendStyle.Left, QgsLegendStyle.Right):
            legend.setStyleMargin(style, side, 0.18)
    layout.addLayoutItem(legend)
    legend.attemptMove(QgsLayoutPoint(10, 78.5, QgsUnitTypes.LayoutMillimeters))
    legend.attemptResize(QgsLayoutSize(74, 21.5, QgsUnitTypes.LayoutMillimeters))


def main() -> None:
    os.environ.setdefault("PYTHONNOUSERSITE", "1")
    ATTACH_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if LAYER_GPKG.exists():
        LAYER_GPKG.unlink()

    project = QgsProject.instance()
    project.clear()
    project.setCrs(WEB_CRS)

    basemap_url = "https://server.arcgisonline.com/ArcGIS/rest/services/World_Terrain_Base/MapServer/tile/{z}/{y}/{x}"
    basemap = QgsRasterLayer(f"type=xyz&url={basemap_url}&zmin=0&zmax=9", "Esri WorldTerrainBase", "wms")
    if basemap.isValid():
        basemap.setOpacity(1.0)
        project.addMapLayer(basemap)

    adm2 = materialize_vector_layer(
        project, make_boundary_line_layer("ADM2 boundary", "ADM2", "#8a8a8a", 0.08, 0.58)
    )
    adm1 = materialize_vector_layer(
        project, make_boundary_line_layer("ADM1 boundary", "ADM1", "#3f3f3f", 0.20, 0.82)
    )
    country_outline = materialize_vector_layer(project, make_country_outline_layer())
    for layer in (adm2, adm1, country_outline):
        project.addMapLayer(layer)

    event_specs = [
        ("Iran-axis strikes", "circle", "#f7b5b5", "#c91f2c"),
        ("US/Israeli strikes", "circle", "#ffd17f", "#d79000"),
    ]
    groups = read_events()
    event_layers = []
    for name, marker, fill, outline in event_specs:
        layer = materialize_vector_layer(project, make_point_layer(name, groups[name], marker, fill, outline))
        project.addMapLayer(layer)
        event_layers.append(layer)

    city_labels = materialize_vector_layer(project, make_city_label_layer())
    project.addMapLayer(city_labels)

    layout = QgsPrintLayout(project)
    layout.initializeDefaults()
    layout.setName("Figure 1 QGIS Study Area Event Map")
    layout.pageCollection().page(0).setPageSize(QgsLayoutSize(183, 114.5, QgsUnitTypes.LayoutMillimeters))
    project.layoutManager().addLayout(layout)

    map_item = QgsLayoutItemMap(layout)
    map_item.setRect(0, 0, 171, 105.5)
    map_item.setExtent(web_extent(project))
    # QgsLayoutItemMap renders the first layer above later layers in this setup.
    # Keep the XYZ basemap last so it does not wash out boundaries and event markers.
    overlay_layers = [city_labels, *reversed(event_layers), country_outline, adm1, adm2]
    layers = [*overlay_layers, basemap] if basemap.isValid() else overlay_layers
    map_item.setLayers(layers)
    map_item.setFrameEnabled(True)
    map_item.setFrameStrokeColor(QColor("#1a1a1a"))
    map_item.setFrameStrokeWidth(QgsLayoutMeasurement(0.48, QgsUnitTypes.LayoutMillimeters))
    layout.addLayoutItem(map_item)
    map_item.attemptMove(QgsLayoutPoint(6, 4, QgsUnitTypes.LayoutMillimeters))
    map_item.attemptResize(QgsLayoutSize(171, 105.5, QgsUnitTypes.LayoutMillimeters))
    add_grid(map_item)

    scale_bar = QgsLayoutItemScaleBar(layout)
    scale_bar.setStyle("Single Box")
    scale_bar.setLinkedMap(map_item)
    scale_bar.setUnits(QgsUnitTypes.DistanceKilometers)
    scale_bar.setSegmentSizeMode(QgsScaleBarSettings.SegmentSizeFixed)
    scale_bar.setUnitsPerSegment(200)
    scale_bar.setNumberOfSegments(3)
    scale_bar.setNumberOfSegmentsLeft(0)
    scale_bar.setUnitLabel("km")
    scale_bar.setFont(QFont("Arial", 5))
    scale_bar.setLineWidth(0.30)
    scale_bar.setHeight(2.0)
    scale_bar.setLabelVerticalPlacement(QgsScaleBarSettings.LabelBelowSegment)
    scale_bar.setLabelHorizontalPlacement(QgsScaleBarSettings.LabelCenteredEdge)
    scale_bar.setLabelBarSpace(1.0)
    layout.addLayoutItem(scale_bar)
    scale_bar.attemptMove(QgsLayoutPoint(43, 101, QgsUnitTypes.LayoutMillimeters))
    scale_bar.attemptResize(QgsLayoutSize(42, 8, QgsUnitTypes.LayoutMillimeters))

    arrow_path = QGIS_NORTH_ARROW if QGIS_NORTH_ARROW.exists() else NORTH_ARROW
    if arrow_path.exists():
        arrow = QgsLayoutItemPicture(layout)
        arrow.setId("North arrow")
        arrow.setPicturePath(str(arrow_path))
        layout.addLayoutItem(arrow)
        arrow.attemptMove(QgsLayoutPoint(164.5, 12.2, QgsUnitTypes.LayoutMillimeters))
        arrow.attemptResize(QgsLayoutSize(10.8, 11.3, QgsUnitTypes.LayoutMillimeters))

    keep_names = [name for name, *_ in event_specs] + ["ADM1 boundary", "ADM2 boundary", "Study area"]
    add_legend(layout, map_item, keep_names)

    project_path = OUT_DIR / "figure1_study_area_isw_event_map_qgis_osm_admin_v4.qgz"
    png_path = ATTACH_DIR / "figure1_study_area_isw_event_map_qgis.png"
    project.write(str(project_path))

    exporter = QgsLayoutExporter(layout)
    image_settings = QgsLayoutExporter.ImageExportSettings()
    image_settings.dpi = 600
    if png_path.exists():
        png_path.unlink()
    image_result = exporter.exportToImage(str(png_path), image_settings)
    if image_result != QgsLayoutExporter.Success:
        raise RuntimeError(f"QGIS image export failed: image={image_result}")
    print(f"project={project_path}")
    print(f"png={png_path}")


if __name__ == "__main__":
    from qgis.core import QgsApplication, QgsFeatureRequest, QgsLayerTreeLayer, QgsLegendStyle, QgsLayoutMeasurement, QgsPointXY, QgsSingleSymbolRenderer

    app = QgsApplication([], False)
    app.initQgis()
    try:
        main()
    finally:
        app.exitQgis()
