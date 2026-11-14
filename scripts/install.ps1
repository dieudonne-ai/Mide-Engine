# Windows installer: creates a virtualenv in %USERPROFILE%\.mide\venv and installs MIDE Engine.
# Usage: powershell -ExecutionPolicy Bypass -File scripts\install.ps1 [-Extras "ui,llm,rag"]
param([string]$Extras = "ui")
$ErrorActionPreference = "Stop"
$HomeDir = if ($env:MIDE_HOME) { $env:MIDE_HOME } else { Join-Path $env:USERPROFILE ".mide" }
if (-not (Get-Command python -ErrorAction SilentlyContinue)) { throw "Python 3.11+ is required." }
python -c "import sys; sys.exit(sys.version_info < (3, 11))"
if ($LASTEXITCODE -ne 0) { throw "Python 3.11+ is required." }
New-Item -ItemType Directory -Force -Path $HomeDir | Out-Null
python -m venv "$HomeDir\venv"
& "$HomeDir\venv\Scripts\pip.exe" install --upgrade pip
$Root = Split-Path -Parent $PSScriptRoot
& "$HomeDir\venv\Scripts\pip.exe" install "$Root[$Extras]"
Write-Host "Installed. Run: $HomeDir\venv\Scripts\mide.exe doctor"
