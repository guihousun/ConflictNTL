# Portability Notes

ConflictNTL is distributed as two separate agent-facing layers plus workflow
scripts:

- `skills/conflict-ntl-analysis/`: procedural knowledge, orchestration logic,
  validation rules, and workflow-specific scripts.
- `mcp/conflictntl-gis-tools/`: standalone MCP server with atomic reusable GIS
  tools.
- optional global `qgis` MCP server: QGIS-native project, layer, processing,
  and layout operations.

The MCP server must be registered separately by the client. The skill teaches
an agent when and how to use it.

## New-Machine Contract

A new Codex machine should be able to use this package after preparing:

- the skill folder;
- the standalone `conflictntl-gis-tools` MCP server;
- optionally the global `qgis` MCP server for QGIS project/layout work;
- an empty ConflictNTL project root with `inputs/`, `data/`, `attachments/`,
  and `outputs/`;
- `inputs/ISW_storymap_events_2026-02-27_2026-04-27.csv` or a configured
  `CONFLICTNTL_EVENTS_CSV`;
- a Python environment for MCP GIS tools using
  `mcp/conflictntl-gis-tools/requirements.txt`;
- a workflow Python/GIS environment using `requirements-workflow.txt`;
- authenticated Earth Engine credentials and `GEE_DEFAULT_PROJECT_ID`;
- QGIS Python only for QGIS layout/filtering operations.

## MCP Decision

Use skill instructions when the task is: "decide the workflow sequence, choose
which tool or script to run, and validate manuscript outputs."

Use MCP tools when the task is an atomic capability:

- `download_geoboundary`
- `inspect_vector`
- `filter_points_by_polygon`
- `spatial_join_points_to_admin`
- `make_aeqd_point_buffers`
- `dissolve_overlapping_polygons`

Do not expose these as MCP tools:

- complete 3 km reproduction;
- Figure 3 or Figure 4 publication export;
- Table 1 manuscript-specific reconstruction;
- multi-step ConflictNTL orchestration.

Those are scripts controlled by the skill, because they encode manuscript
choices, current figure aesthetics, expected filenames, and project-specific
validation gates.

## Filtering Protocol

Fresh event filtering must use this order:

```text
raw events
  -> date and valid point filter
  -> geoBoundaries ADM0 filter for IRN/ISR
  -> HOTOSM building filter
  -> LLM NTL-applicability filter
  -> ADM1/ADM2 labels for region naming
```

ADM1/ADM2 labels are context fields for tables and figures. They should not be
described as the first screening gate.

## Recommended Open-Source Layout

```text
ConflictNTL/
├── README.md
├── skills/
│   └── conflict-ntl-analysis/
├── mcp/
│   └── conflictntl-gis-tools/
├── figures/
└── docs/
```

The skill folder should stay lean:

```text
conflict-ntl-analysis/
├── SKILL.md
├── agents/openai.yaml
├── scripts/
└── references/
```

Do not put large raw data, manuscript drafts, or bulky tile caches inside the
skill. Provide example data separately.

## Current Portability Status

- The 3 km Table 1 and Figure 4 scripts can run from the skill package after
  `events_geoboundaries_v2_downstream.csv` exists.
- The event filtering script now uses geoBoundaries and no longer calls the
  legacy OSM wrapper.
- The standalone filtering path is runnable, but any refreshed filtered-event
  table must be compared against the manuscript-authoritative event IDs before
  replacing accepted outputs.
- Some figure scripts still preserve manuscript-specific style and filenames;
  this is intentional and belongs in `scripts/`, not in MCP tools.
