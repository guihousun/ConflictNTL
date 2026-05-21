#!/usr/bin/env python3
"""QGIS Layout Item Mover — CLI tool for moving layout items.

Usage:
    # Move legend down by 2mm
    python qgis-layout-move.py --project figure1.qgz --layout "Main" --item legend --dy 2

    # Move north arrow up by 2mm
    python qgis-layout-move.py --project figure1.qgz --layout "Main" --item north-arrow --dy -2

    # Move to absolute position
    python qgis-layout-move.py --project figure1.qgz --layout "Main" --item legend --x 10 --y 85

    # List available item types
    python qgis-layout-move.py --list-types
"""

import argparse
import sys
from pathlib import Path

# QGIS Python path
QGIS_PYQGIS = r"C:\Program Files\QGIS 3.38.3\apps\qgis\python"
if QGIS_PYQGIS not in sys.path:
    sys.path.insert(0, QGIS_PYQGIS)

from qgis.core import (
    QgsApplication,
    QgsProject,
    QgsLayoutPoint,
    QgsUnitTypes,
)


ITEM_TYPES = {
    "legend": "QgsLayoutItemLegend",
    "north-arrow": "QgsLayoutItemPicture",
    "scalebar": "QgsLayoutItemScaleBar",
    "map": "QgsLayoutItemMap",
    "label": "QgsLayoutItemLabel",
}


def move_item(project_path: str, layout_name: str, item_type: str,
              dx: float = 0.0, dy: float = 0.0,
              x: float | None = None, y: float | None = None) -> dict:
    """Move a layout item by delta or to absolute position."""
    app = QgsApplication([], False)
    app.initQgis()

    try:
        project = QgsProject.instance()
        if not project.read(project_path):
            raise RuntimeError(f"Failed to read project: {project_path}")

        layout = None
        for l in project.layoutManager().printLayouts():
            if l.name() == layout_name:
                layout = l
                break

        if layout is None:
            raise RuntimeError(f"Layout not found: {layout_name}")

        target_class = ITEM_TYPES.get(item_type.lower())
        if not target_class:
            raise RuntimeError(
                f"Unknown item type: {item_type}. Use one of: {', '.join(ITEM_TYPES.keys())}"
            )

        matched_item = None
        for item in layout.items():
            if type(item).__name__ == target_class:
                matched_item = item
                break

        if matched_item is None:
            raise RuntimeError(f"No {item_type} found in layout: {layout_name}")

        pos = matched_item.positionWithUnits()
        new_x = x if x is not None else pos.x() + dx
        new_y = y if y is not None else pos.y() + dy

        matched_item.attemptMove(
            QgsLayoutPoint(new_x, new_y, QgsUnitTypes.LayoutMillimeters)
        )

        project.write(project_path)

        result = {
            "layout": layout_name,
            "item": item_type,
            "old_position": {"x": round(pos.x(), 2), "y": round(pos.y(), 2)},
            "new_position": {"x": round(new_x, 2), "y": round(new_y, 2)},
        }

        return result

    finally:
        app.exitQgis()


def main():
    parser = argparse.ArgumentParser(
        description="Move QGIS layout items by delta or to absolute position."
    )
    parser.add_argument("--project", required=True, help="Path to .qgz project file")
    parser.add_argument("--layout", required=True, help="Layout name")
    parser.add_argument("--item", required=True, help=f"Item type: {', '.join(ITEM_TYPES.keys())}")
    parser.add_argument("--dx", type=float, default=0.0, help="Delta X in mm")
    parser.add_argument("--dy", type=float, default=0.0, help="Delta Y in mm")
    parser.add_argument("--x", type=float, default=None, help="Absolute X in mm")
    parser.add_argument("--y", type=float, default=None, help="Absolute Y in mm")
    parser.add_argument("--list-types", action="store_true", help="List available item types")

    args = parser.parse_args()

    if args.list_types:
        print("Available item types:")
        for name, cls in ITEM_TYPES.items():
            print(f"  {name:<12} ({cls})")
        return

    result = move_item(
        project_path=args.project,
        layout_name=args.layout,
        item_type=args.item,
        dx=args.dx,
        dy=args.dy,
        x=args.x,
        y=args.y,
    )

    print(f"Moved {result['item']} in layout '{result['layout']}':")
    print(f"  Old position: x={result['old_position']['x']}, y={result['old_position']['y']}")
    print(f"  New position: x={result['new_position']['x']}, y={result['new_position']['y']}")


if __name__ == "__main__":
    main()
