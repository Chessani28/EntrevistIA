param([ValidateSet('mock','ollama')][string]$Provider = 'ollama')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$previousProvider = $env:AIADMISSION_PROVIDER
$python = Join-Path $projectRoot '.venv/Scripts/python.exe'
if (!(Test-Path -LiteralPath $python)) { $python = 'python' }
try {
    $env:AIADMISSION_PROVIDER = $Provider
    Push-Location $projectRoot
    try { & $python -m backend.run }
    finally { Pop-Location }
} finally { $env:AIADMISSION_PROVIDER = $previousProvider }
