# Portability Notes

This skill is a reproducible experiment skill, not a full standalone MCP server.
Use it first as a portable script-and-procedure bundle. Convert to MCP only when
the workflow needs stable programmatic APIs for other agents or services.

## What Must Be Retargeted

When migrating outside the current vault, update:

- project root
- data root
- attachment/output root
- QGIS install path
- conda environment names
- GEE authentication/project settings
- boundary data paths
- manuscript-specific figure names

The bundled scripts currently preserve absolute paths so the original paper
workspace remains reproducible. For open-source release, either:

- replace path constants with CLI arguments, or
- add a small config file consumed by all scripts.

## Recommended Open-Source Layout

```text
ConflictNTL/
├── skills/
│   └── conflict-ntl-analysis/
├── scripts/
├── data/example/
├── docs/
├── requirements/
└── README.md
```

In a Codex skill distribution, keep the actual skill folder lean:

```text
conflict-ntl-analysis/
├── SKILL.md
├── agents/openai.yaml
├── scripts/
└── references/
```

Do not put large raw data, manuscript drafts, or bulky tile caches inside the
skill. Provide example data separately.

## MCP Decision

Use a skill when the main need is: "teach an agent how to run the workflow and
reuse scripts."

Use MCP when the main need is: "expose durable tools with typed arguments and
machine-readable results."

Good future MCP endpoints:

- `fetch_events`
- `screen_events`
- `build_aeqd_clusters`
- `reduce_vnp46a2`
- `make_table1`
- `export_figure3`
- `export_figure4`

MCP is higher maintenance because it needs schema design, versioning, logging,
and error handling. Keep the skill as the first open-source artifact, then wrap
stable scripts as MCP tools after the workflow stops changing.

