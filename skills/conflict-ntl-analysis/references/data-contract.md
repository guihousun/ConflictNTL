# ConflictNTL Data Contract

Use this reference when checking inputs, outputs, or adapting the scripts to a
new conflict case.

## Required Event Fields

The filtered event table must include:

- `event_id`: stable event identifier.
- `longitude`: event longitude in EPSG:4326.
- `latitude`: event latitude in EPSG:4326.
- date field used by the AEQD/NTL scripts for daily event counts.
- country/actor/category fields if Table 1 or figure labels need grouping.

Known pitfall: normalize numeric `event_id` values before joining labels.
Values such as `1.0` and `1` must map to the same key.

## Spatial Requirements

- Source point CRS: EPSG:4326.
- Final buffer construction: local AEQD projection centered on the study event set.
- Buffer radius: current manuscript uses 3 km; 5 km is a sensitivity version.
- Cluster construction: dissolve buffers by connected overlap graph.
- Figure overlays: use dissolved cluster polygons, not centroids or point symbols.

## Boundary Inputs

The current project uses geoBoundaries administrative boundaries for filtering,
labels, and visualization. The event-filtering order is:

```text
geoBoundaries ADM0 -> HOTOSM building footprint -> LLM NTL applicability
```

ADM1/ADM2 labels are added after filtering as reporting context. HOTOSM
building footprints may be used for event relevance filtering, but
administrative boundaries should not be named or described as OSM boundaries in
the current workflow. Administrative boundaries are supporting context, not the
final impact-zone definition.

Current local boundary/cache examples:

```text
${PROJECT_ROOT}/outputs/admin_scale_results/geoboundaries_cache
${PROJECT_ROOT}/data/boundaries
```

## Nighttime-Light Data

Default GEE product and band:

```text
NASA/VIIRS/002/VNP46A2
DNB_BRDF_Corrected_NTL
```

Use the same AOI polygons for daily ANTL extraction, Table 1 summaries, and
Figure 4 daily curves.

## Output Semantics

Table 1 should report top-10 core impact zones, not individual events. The
`n` value is the number of original events assigned to that cluster. If a
cluster spans multiple ADM2 units, name it with the two largest intersecting
ADM2 areas by equal-area intersection, e.g. `Akko&Zefat cluster` or
`Tehran&Karaj cluster`. Normalize duplicate administrative wording before
selecting the two names, e.g. `City of Tehran` -> `Tehran`.

## Common Failure Modes

- Web Mercator buffers distort distances; use AEQD.
- Cluster counts can change if buffers are built from pre-merged polygons
  instead of original event points.
- Missing GEE pixels should be tracked as missing days rather than silently
  interpolated.
- Administrative labels can be misleading near borders; verify multi-city
  clusters against geometry.
