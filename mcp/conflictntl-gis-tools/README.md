# ConflictNTL GIS Tools MCP

This is a standalone MCP server for atomic GIS operations used by
ConflictNTL-style workflows.

The server is intentionally not a complete ConflictNTL workflow runner.
`SKILL.md` should decide the workflow order and call either these generic
tools, the global `qgis` MCP server, or workflow-specific scripts.

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

```json
{
  "mcpServers": {
    "conflictntl-gis-tools": {
      "command": "python",
      "args": ["D:/Research_vault/raw/mcp/conflictntl-gis-tools/server.py"]
    }
  }
}
```
