---
name: conflict-ntl-analysis
description: Reproduce and adapt the ConflictNTL workflow for conflict-event screening, AEQD buffer impact-zone construction, VIIRS VNP46A2 nighttime-light statistics, and publication figures/tables. Use when working on ConflictNTL-style manuscripts, ISW/strike event impacts, QGIS/PyQGIS event screening, GEE VNP46A2 ANTL extraction, top-10 core impact zones, or Figure 1/3/4/Table 1 regeneration.
---

# ConflictNTL Analysis

Use this skill for ConflictNTL-style geospatial nighttime-light experiments:
event ingestion/screening, QGIS spatial filtering, AEQD buffer clustering,
GEE VNP46A2 statistics, Table 1, and publication figures.

## Operating Rules

1. Treat `events_osm_v2_downstream.csv` as the authoritative screened event table after QGIS screening.
2. Build impact zones from original event points in an equal-distance projection. Do not use EPSG:3857 or raw lon/lat buffers for final cluster statistics.
3. Use `NASA/VIIRS/002/VNP46A2` and band `DNB_BRDF_Corrected_NTL` unless the user explicitly changes the product.
4. Keep Table 1, Figure 3 overlays, and Figure 4 curves tied to the same AEQD dissolved cluster polygons.
5. For manuscript figures, self-check layout before finalizing: panel alignment, white space, colorbar labels, hidden/overlapping labels, scale bars, and whether the map still communicates the intended evidence.

## Bundled Scripts

Scripts are in `scripts/`. They are copied from the ConflictNTL Letter project
and may contain absolute project paths. Before migrating to another workspace,
retarget path constants near the top of each script or provide a compatible
directory layout.

- `scripts/qgis_screening/run_osm_v2_pyqgis.py`: QGIS/geoBoundaries V2 event screening.
- `scripts/aeqd_ntl/make_table1_aeqd_3km_clusters_ntl_complete.py`: current 3 km AEQD cluster, GEE ANTL, Table 1.
- `scripts/aeqd_ntl/make_table1_aeqd_5km_clusters_ntl_complete.py`: 5 km sensitivity version.
- `scripts/figures/make_figure3_publication_3km_text13.py`: current 5-band Figure 3 layout.
- `scripts/figures/make_figure3_publication_3km_text13_7band.py`: optional 7-band Figure 3 variant.
- `scripts/figures/export_figure3_v2_admin_ntl_panel_assets.py`: Figure 3 GEE tile/panel asset exporter used by the composite scripts.
- `scripts/figures/make_figure4_aeqd_3km_daily_curves.py`: current 3 km Figure 4 daily curves.
- `scripts/figures/make_figure4_aeqd_daily_curves.py`: base Figure 4 style module imported by the 3 km script.
- `scripts/qgis_layout/`: CLI helpers for direct `.qgz` layout edits.

## Reference Loading

Load only the reference needed for the task:

- For end-to-end reproduction, commands, and expected outputs, read `references/workflow.md`.
- For required input/output files and schema assumptions, read `references/data-contract.md`.
- For figure style, panel layout, color breaks, and user preferences, read `references/figure-style.md`.
- For migration or open-source packaging decisions, read `references/portability.md`.

## Minimal Workflow

1. Confirm the project root, data root, attachment root, and Python/QGIS runtimes.
2. If event screening must be refreshed, run the QGIS screening script with QGIS Python.
3. Run the chosen AEQD script, normally 3 km for the current manuscript and 5 km for sensitivity.
4. Regenerate Table 1 and figures from the same AEQD output directory.
5. Validate counts, cluster polygons, and figure outputs before reporting completion.
