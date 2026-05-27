# ConflictNTL GIS Tools MCP

This is a standalone MCP server for atomic GIS operations used by
ConflictNTL-style workflows.

The server is intentionally not a complete ConflictNTL workflow runner.
`SKILL.md` should decide the workflow order.

Prefer the global `qgis` MCP server for QGIS-native work: project loading,
layer management, QGIS Processing, layout creation/export, QML styles, canvas
rendering, and custom PyQGIS. Use this server for reusable headless GIS
operations that are not better covered by QGIS MCP.

## Tools

- `describe_tools`
- `validate_environment`
- `download_geoboundary`
- `inspect_vector`
- `filter_points_by_polygon`
- `spatial_join_points_to_admin`
- `make_aeqd_point_buffers`
- `dissolve_overlapping_polygons`

## Run

```powershell
python -m pip install -r "D:/Research_vault/raw/mcp/conflictntl-gis-tools/requirements.txt"
python "D:/Research_vault/raw/mcp/conflictntl-gis-tools/server.py"
```

Example client entry:

```toml
[mcp_servers.conflictntl-gis-tools]
command = "python"
args = ["D:/Research_vault/raw/mcp/conflictntl-gis-tools/server.py"]
```

After editing the Codex MCP config, refresh or restart the Codex session. If
loaded, this server should expose a namespace similar to
`mcp__conflictntl_gis_tools__...`.
