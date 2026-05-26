# ConflictNTL Reproduction Workflow

This reference captures the current reproducible pipeline used by the
ConflictNTL Letter project.

## Project Defaults

Expected portable project layout:

```text
${PROJECT_ROOT}/inputs/ISW_storymap_events_2026-02-27_2026-04-27.csv
${PROJECT_ROOT}/data/event_screening_geoboundaries_v2_qgis/
${PROJECT_ROOT}/attachments/
${PROJECT_ROOT}/outputs/
```

Bundled workflow scripts are under:

```text
${SKILL_ROOT}/scripts
```

The atomic MCP server is separate from the skill:

```text
${REPO_ROOT}/mcp/conflictntl-gis-tools/server.py
```

## Periods

```text
preconflict: 2026-02-14 to 2026-02-27
conflict:    2026-02-28 to 2026-04-07
ceasefire:   2026-04-08 to 2026-04-21
```

## Runtime Pattern

Register MCP tools separately from this skill:

```powershell
python "${REPO_ROOT}/mcp/conflictntl-gis-tools/server.py"
```

Use MCP tools for atomic GIS operations. Use direct script calls for
publication-specific workflow steps:

```powershell
python "${SKILL_ROOT}/scripts/qgis_screening/run_geoboundaries_v2_pyqgis.py"
python "${SKILL_ROOT}/scripts/aeqd_ntl/make_table1_aeqd_3km_clusters_ntl_complete.py"
python "${SKILL_ROOT}/scripts/figures/export_figure3_v2_admin_ntl_panel_assets.py" --refresh-tiles
python "${SKILL_ROOT}/scripts/figures/make_figure3_publication_3km_text13.py"
python "${SKILL_ROOT}/scripts/figures/make_figure4_aeqd_3km_daily_curves.py"
```

QGIS project or layout edits should use the global `qgis` MCP server or QGIS
Python CLI rather than the ConflictNTL GIS MCP server.

## Authoritative Flow

```text
ISW StoryMap events
  -> date-window and valid-coordinate checks
  -> geoBoundaries ADM0 filter for Iran and Israel
  -> HOTOSM building-footprint intersection filter
  -> LLM NTL-applicability filter
  -> ADM1/ADM2 labels for reporting context
  -> events_geoboundaries_v2_downstream.csv
  -> AEQD 3 km event buffers
  -> dissolved connected core impact polygons
  -> GEE VNP46A2 daily ANTL
  -> Table 1, Figure 3 overlay, Figure 4 daily curves
```

## Current 3 km Outputs

Output directory:

```text
${PROJECT_ROOT}/data/event_screening_geoboundaries_v2_qgis/buffer_ntl_aeqd3
```

Expected key outputs:

- `aeqd_3km_clusters_all_264.csv`
- `aeqd_3km_clusters_all_264.geojson`
- `aeqd_3km_membership_2383_points.csv`
- `aeqd_3km_top10_clusters.geojson`
- `aeqd_3km_top10_daily_antl.csv`
- `aeqd_3km_top10_daily_panel.csv`
- `aeqd_3km_top10_period_summary.csv`
- `aeqd_3km_top10_table1_complete.csv`

## Optional 5 km Sensitivity Outputs

The current letter uses 3 km buffers only. The 5 km script is retained for
method sensitivity checks and older drafts, but a fresh-machine manuscript
reproduction should not run it unless explicitly requested.

## Validation Checklist

- `events_geoboundaries_v2_downstream.csv` has the manuscript-authoritative
  filtered event count before it is used for Table 1 or figures.
- If event filtering is rerun from raw events, compare downstream event IDs
  against the manuscript table before replacing accepted outputs.
- AEQD cluster count matches the selected buffer version.
- Top-10 cluster GeoJSON is dissolved polygon geometry, not point markers.
- Table 1 regions and event counts come from the same top-10 clusters used by
  figures.
- Figure 3 overlays clusters only on difference panels and zooms, not raw
  intensity panels.
- Figure 4 city/cluster labels match Table 1.
- The publication Figure 4 exported from the clean 3 km run is
  `attachments/v2_figure4_daily_curves_aeqd3km.*`.
