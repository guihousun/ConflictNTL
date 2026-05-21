#!/usr/bin/env pwsh
<#
.SYNOPSIS
    cli-anything-qgis wrapper for Windows QGIS environment.

.DESCRIPTION
    This script wraps cli-anything-qgis to automatically set up the QGIS
    Python environment before execution. It handles o4w_env.bat, PYTHONPATH,
    and delegates to the QGIS Python interpreter.

    Place this script in a directory on your PATH (e.g. D:\Tools) and rename
    to cli-anything-qgis.ps1 for direct invocation.

.EXAMPLE
    cli-anything-qgis --json --project demo.qgz layout list
    cli-anything-qgis --project demo.qgz export image out.png --layout Main --dpi 600
    cli-anything-qgis repl
#>

$ErrorActionPreference = "Stop"

# QGIS installation paths
$QGIS_ROOT = "C:\Program Files\QGIS 4.0.2"
$QGIS_PYTHON = "$QGIS_ROOT\apps\Python312\python.exe"
$QGIS_PYQGIS = "$QGIS_ROOT\apps\qgis\python"
$O4W_ENV = "$QGIS_ROOT\bin\o4w_env.bat"

# Validate QGIS installation
if (-not (Test-Path $QGIS_PYTHON)) {
    Write-Error "QGIS Python not found: $QGIS_PYTHON`nPlease install QGIS or update QGIS_ROOT in this script."
    exit 1
}

if (-not (Test-Path $O4W_ENV)) {
    Write-Error "o4w_env.bat not found: $O4W_ENV`nPlease install QGIS or update QGIS_ROOT in this script."
    exit 1
}

# Run o4w_env.bat to set up GDAL, PROJ, etc.
# We capture its environment and merge into current process
$env:OSGEO4W_ROOT = $QGIS_ROOT

# Set PYTHONPATH to include PyQGIS
$env:PYTHONPATH = "$QGIS_PYQGIS;$env:PYTHONPATH"

# Also ensure qgis_process is on PATH
$env:PATH = "$QGIS_ROOT\apps\qgis\bin;$QGIS_ROOT\bin;$env:PATH"

# Run cli-anything-qgis via QGIS Python module
& $QGIS_PYTHON -m cli_anything.qgis.qgis_cli @args

exit $LASTEXITCODE
