param([int]$Port = 8765, [switch]$SkipInstall)
$ErrorActionPreference = 'Stop'
$crumbleRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $crumbleRoot
$crumblePython = Join-Path $crumbleRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $crumblePython)) {
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.11 or newer is required.' }
}
if (-not $SkipInstall) {
    & $crumblePython -m pip install -e '.[dev]'
    if ($LASTEXITCODE -ne 0) { throw 'Crumble dependency installation failed.' }
}
if (-not (Test-Path -LiteralPath 'work\crumble.sqlite')) {
    & $crumblePython -m crumble.cli --workspace work demo
    if ($LASTEXITCODE -ne 0) { throw 'The demo could not be prepared.' }
}
Write-Host "Project Crumble: http://127.0.0.1:$Port"
& $crumblePython -m crumble.cli --workspace work serve --port $Port
