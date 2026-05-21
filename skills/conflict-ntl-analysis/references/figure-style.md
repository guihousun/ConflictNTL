# ConflictNTL Figure Style

Use this reference for manuscript map and chart regeneration.

## General Figure Rules

- Prefer Times New Roman or a serif fallback for manuscript figures.
- Keep panel labels and colorbar labels visually consistent across subplots.
- Reduce unused white space, but keep a small margin between raster content and axes.
- Preserve lat/lon labels, but remove gridlines when they reduce clarity.
- Self-check the exported PNG/TIFF visually before reporting completion.

## Figure 3 Current Style

Raw nighttime-light intensity:

```python
MEAN_BREAKS = [0, 3, 10, 30, 80, 245]
```

Preferred label:

```text
NTL intensity (nW/cm2/sr)
```

Difference maps use a 5-band diverging scheme centered on near-zero change.
The currently preferred semantic classes are:

```text
<-10, -10~-3, -3~3, 3~10, >10
```

Preferred label:

```text
NTL difference (nW/cm2/sr)
```

Optional 7-band variant:

```python
MEAN_BREAKS = [0, 3, 7, 10, 20, 50, 80, 255]
MEAN_COLORS = ["#000000", "#242424", "#464646", "#707070", "#9a9a9a", "#c5c5c5", "#ffffff"]
DIFF_BREAKS = [-1e9, -10, -3, -1, 1, 3, 10, 1e9]
DIFF_COLORS = ["#1f2f99", "#2c7fb8", "#7fcdbb", "#fff2d8", "#fdae61", "#f46d43", "#d73027"]
```

## Figure 3 Layout Preferences

- Iran row: pre-war, conflict, difference.
- Israel row: pre-war, conflict, difference, plus Tehran and Tel Aviv zooms in the right column.
- Raw intensity panels should not include administrative boundaries in the 7-band no-admin variant.
- Difference panels may include administrative boundaries, slightly darker and thicker than raw-map context.
- Top-10 cluster overlays should appear only on difference maps and zooms.
- Cluster overlays should be true dissolved buffer polygons, dashed, and not too thick in global Iran panel C.
- Tel Aviv zoom should be focused enough to avoid empty space and should match Tehran zoom width.
- Do not add red connector lines or panel labels if the user plans to add them manually.

## Figure 1 QGIS Layout Preferences

- Directly patch `.qgz` layout with QGIS CLI when only layout items change.
- The user prefers a compact legend inside the map, above the scale bar.
- Scale bar style: segmented black/white, label below, km units.
- North arrow: clean, compact, and slightly inset from the upper-right corner.
- Event point symbols should stay readable but not dominate the basemap.

## Figure 4 Style

- Use the `_regenerate_v2_figures_567.py` visual language when possible.
- Use large, readable labels and a horizontal legend.
- Ensure plotted cities/cluster names match the current Table 1 cluster labels.

