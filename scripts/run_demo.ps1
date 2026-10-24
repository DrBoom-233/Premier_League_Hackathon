param([int]$Port = 8000)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
Set-Location $projectRoot
$pythonPath = Join-Path $projectRoot '.venv/Scripts/python.exe'
if (!(Test-Path -LiteralPath $pythonPath)) {
    throw 'Create .venv and install requirements.txt first. See README.md.'
}
if (!(Test-Path -LiteralPath 'src/frontend/dist/index.html')) {
    throw 'Build frontend first: cd src/frontend; npm ci; npm run build'
}
& $pythonPath -m uvicorn src.backend.app:app --host 127.0.0.1 --port $Port --workers 1
