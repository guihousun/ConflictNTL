# ConflictNTL Reproduction Workflow

This reference captures the current reproducible pipeline used by the
ConflictNTL Letter project.

## Project Defaults

Current project workspace:

```text
D:\Research_vault\raw\writing\conflictntl
```

Current script source of truth:

```text
D:\Research_vault\raw\writing\conflictntl\scripts
```

Mature upstream script archive:

```text
D:\Research_vault\raw\code\NTL\scripts\conflictntl-letter
```

## Runtime Defaults

QGIS screening uses QGIS Python:

```powershell
& "C:\Program Files\QGIS 4.0.2\apps\Python312\python.exe" `
  "D:\Research_vault\raw\writing\conflictntl\scripts\qgis_screening\run_osm_v2_pyqgis.py"
```

GEE/NTL scripts normally use the `NTL-GPT-Stable` conda environment:

```powershell
& "C:\Users\27334\miniconda3\Scripts\conda.exe" run -n NTL-GPT-Stable python `
  "D:\Research_vault\raw\writing\conflictntl\scripts\aeqd_ntl\make_table1_aeqd_3km_clusters_ntl_complete.py"
```

Figure 3 currently uses the `ntlgpt` environment:

```powershell
& "C:\Users\27334\miniconda3\envs\ntlgpt\python.exe" `
  "D:\Research_vault\raw\writing\conflictntl\scripts\figures\make_figure3_publication_3km_text13.py"
```

Figure 4:

```powershell
& "C:\Users\27334\miniconda3\Scripts\conda.exe" run -n NTL-GPT-Stable python `
  "D:\Research_vault\raw\writing\conflictntl\scripts\figures\make_figure4_aeqd_3km_daily_curves.py"
```

## Authoritative Flow

```text
ISW StoryMap events
  -> LLM NTL applicability labels
  -> HOTOSM/OSM building intersection filter
  -> QGIS/geoBoundaries spatial screening
  -> events_osm_v2_downstream.csv (2383 events)
  -> AEQD 3 km or 5 km event buffers
  -> dissolved connected core impact polygons
  -> GEE VNP46A2 daily ANTL
  -> Table 1, Figure 3 overlay, Figure 4 daily curves
```

## Current 3 km Outputs

Output directory:

```text
D:\Research_vault\raw\writing\conflictntl\data\event_screening_geoboundaries_v2_qgis\buffer_ntl_aeqd3
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

## Current 5 km Sensitivity Outputs

Output directory:

```text
D:\Research_vault\raw\writing\conflictntl\data\event_screening_geoboundaries_v2_qgis\buffer_ntl_aeqd5
```

Expected key outputs:

- `aeqd_5km_clusters_all_184.csv`
- `aeqd_5km_clusters_all_184.geojson`
- `aeqd_5km_membership_2383_points.csv`
- `aeqd_5km_top10_clusters.geojson`
- `aeqd_5km_top10_daily_antl.csv`
- `aeqd_5km_top10_daily_panel.csv`
- `aeqd_5km_top10_period_summary.csv`
- `aeqd_5km_top10_table1_complete.csv`

## Validation Checklist

- `events_osm_v2_downstream.csv` has 2383 event records.
- AEQD cluster count matches the selected buffer version.
- Top-10 cluster GeoJSON is dissolved polygon geometry, not point markers.
- Table 1 regions and event counts come from the same top-10 clusters used by figures.
- Figure 3 overlays clusters only on difference panels and zooms, not on raw intensity panels.
- Figure 4 city/cluster labels match Table 1.

