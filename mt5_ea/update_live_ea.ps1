# Update the live EA to the latest main: stop -> git pull -> start again (2026-10-24).
# If the pull fails, the EA is started again on the version it had.
param([string]$Kind = "demo")
$repo = Split-Path -Parent $PSScriptRoot
& (Join-Path $PSScriptRoot "stop_live_ea.ps1") -Kind $Kind
Write-Host "Getting the latest main from GitHub..." -ForegroundColor Cyan
git -C $repo pull --ff-only origin main
if ($LASTEXITCODE -ne 0) { Write-Host "Update failed (see above). Starting the EA on the current version." -ForegroundColor Red }
else { git -C $repo log --oneline -3 }
$bat = Join-Path $PSScriptRoot ("START_LIVE_EA_{0}.bat" -f $(if ($Kind -eq "live") { "REAL" } else { "DEMO" }))
Start-Process explorer.exe -ArgumentList "`"$bat`""      # opens the usual EA window
Write-Host "EA started in its own window." -ForegroundColor Green
