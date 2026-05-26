---
name: conflict-ntl-analysis
description: Reproduce and adapt ConflictNTL-style conflict-event nighttime-light analyses, including event filtering, equal-distance impact zones, VIIRS VNP46A2 statistics, Table 1, and manuscript figures.
---

# ConflictNTL Analysis

Use this skill to orchestrate ConflictNTL-style geospatial nighttime-light
workflows. The skill provides workflow knowledge and sequencing. It does not
turn the whole workflow into one black-box tool.

## Layer Boundary

- `SKILL.md` and `references/`: workflow logic, decision rules, expected
  outputs, validation checks, and when to call each capability.
- `mcp/conflictntl-gis-tools`: separately registered MCP server for atomic,
  reusable GIS operations such as geoBoundary download, point-in-polygon joins,
  AEQD buffers, and dissolved buffer components.
- global `qgis` MCP server: use for QGIS project/layer/layout operations when
  available, especially `.qgz` layout edits and QGIS-native processing.
- `scripts/`: project/workflow-specific code that is too specialized to expose
  as generic MCP tools, such as Table 1 reconstruction and publication Figure
  3/4 exports.

## Operating Rules

1. Event filtering order is fixed unless the user changes the protocol:
   geoBoundaries ADM0 containment -> HOTOSM building-footprint filter -> LLM
   NTL-applicability filter. ADM1/ADM2 labels are reporting context, not a
   prior filtering gate.
2. Treat `events_geoboundaries_v2_downstream.csv` as the filtered event table
   used by the current manuscript.
3. Build impact zones from original event points in an equal-distance
   projection. Do not use EPSG:3857 or raw lon/lat buffers for final cluster
   statistics.
4. Use `NASA/VIIRS/002/VNP46A2` and band `DNB_BRDF_Corrected_NTL` unless the
   user explicitly changes the product.
5. Keep Table 1, Figure 3 overlays, and Figure 4 curves tied to the same AEQD
   dissolved cluster polygons.
6. Use the current manuscript periods unless instructed otherwise: preconflict
   2026-02-14 to 2026-02-27, conflict 2026-02-28 to 2026-04-07, and ceasefire
   2026-04-08 to 2026-04-21.
7. For manuscript figures, self-check layout before finalizing: panel
   alignment, white space, colorbar labels, hidden/overlapping labels, scale
   bars, and whether the map still communicates the intended evidence.

## Tool Selection

Use the standalone MCP tools when the task is atomic and reusable:

- download or inspect geoBoundaries files;
- filter points by polygons;
- attach admin attributes to event points;
- create AEQD point buffers;
- dissolve overlapping buffers into connected polygons.

Use the global `qgis` MCP server or QGIS CLI when the task needs QGIS project
state, layers, layouts, print composer items, or `.qgz` edits.

Use bundled scripts when the task is workflow-specific:

- `scripts/qgis_screening/run_geoboundaries_v2_pyqgis.py`: event filtering
  entrypoint using geoBoundaries ADM0, HOTOSM building labels, and LLM labels.
- `scripts/aeqd_ntl/make_table1_aeqd_3km_clusters_ntl_complete.py`: current 3
  km AEQD clusters, GEE ANTL, and Table 1.
- `scripts/aeqd_ntl/make_table1_aeqd_5km_clusters_ntl_complete.py`: optional
  5 km sensitivity/legacy version.
- `scripts/figures/export_figure3_v2_admin_ntl_panel_assets.py`: Figure 3 GEE
  tile and panel asset refresh.
- `scripts/figures/make_figure3_publication_3km_text13.py`: current 5-band
  Figure 3 layout.
- `scripts/figures/make_figure3_publication_3km_text13_7band.py`: optional
  7-band Figure 3 variant.
- `scripts/figures/make_figure4_aeqd_3km_daily_curves.py`: current 3 km Figure
  4 daily curves.
- `scripts/qgis_layout/`: direct `.qgz` layout-item edits.

## Minimal Workflow

1. Confirm project root, data root, attachments root, Python/GIS runtimes, GEE
   project, and whether `conflictntl-gis-tools` and global `qgis` MCP are
   connected.
2. If event filtering must be refreshed, run the filtering script or combine
   atomic MCP calls in this order: ADM0 -> building -> LLM.
3. Run the selected AEQD script, normally 3 km for the current manuscript.
4. Regenerate Table 1 and figures from the same AEQD output directory.
5. Validate event counts, cluster polygons, region labels, and figure outputs
   before reporting completion.

## Reference Loading

- End-to-end commands and expected outputs: `references/workflow.md`.
- Input/output schemas and file contracts: `references/data-contract.md`.
- Figure style and layout preferences: `references/figure-style.md`.
- Open-source packaging and portability: `references/portability.md`.
