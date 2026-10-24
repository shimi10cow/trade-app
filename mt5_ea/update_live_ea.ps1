# Update the live EAs to the latest main (2026-10-24): stop the running ones (demo / live) -> git pull -> start the same ones again.
# Both run the same program, so both are replaced together. If the pull fails, they start again on the version they had.
$repo = Split-Path -Parent $PSScriptRoot
$data = Join-Path $env:USERPROFILE "TradeEA_data"
function Running([string]$kind) {
    $f = Join-Path $data ("live_{0}.pid" -f $kind)
    if (-not (Test-Path $f)) { return $false }
    $p = Get-CimInstance Win32_Process -Filter ("ProcessId={0}" -f ((Get-Content $f -Raw).Trim())) -ErrorAction SilentlyContinue
    return [bool]($p -and $p.CommandLine -match 'start_live_ea\.ps1')
}
$kinds = @("demo", "live") | Where-Object { Running $_ }
if (-not $kinds) { Write-Host "No EA is running: only getting the latest program." -ForegroundColor Yellow }
foreach ($k in $kinds) { & (Join-Path $PSScriptRoot "stop_live_ea.ps1") -Kind $k }
Write-Host "Getting the latest main from GitHub..." -ForegroundColor Cyan
git -C $repo pull --ff-only origin main
if ($LASTEXITCODE -ne 0) { Write-Host "Update failed (see above). Starting the EA on the current version." -ForegroundColor Red }
else { git -C $repo log --oneline -3 }
foreach ($k in $kinds) {
    # the REAL start asks for a confirmation; here the EA was already running, so start it directly in its own window
    $args_ = "-NoExit -NoProfile -ExecutionPolicy Bypass -File `"{0}`" -Kind {1}" -f (Join-Path $PSScriptRoot "start_live_ea.ps1"), $k
    Start-Process powershell.exe -ArgumentList $args_ -WorkingDirectory $PSScriptRoot
    Write-Host ("{0} EA started in its own window." -f $k) -ForegroundColor Green
}
