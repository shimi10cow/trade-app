$ErrorActionPreference = "Stop"
$login=[Environment]::GetEnvironmentVariable("EA_LIVE_LOGIN","User")
$server=[Environment]::GetEnvironmentVariable("EA_LIVE_SERVER","User")
if (-not $login -or -not $server) { throw "LIVE account lock is not configured." }
$env:EA_LIVE_LOGIN=$login
$env:EA_LIVE_SERVER=$server
$env:EA_LIVE_ARMED="false"
$env:EA_DRY_RUN="true"
Write-Host "Hybrid EA - FINAL PRE-LIVE CHECK (NO ORDERS)" -ForegroundColor Cyan
py .\preflight.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
py .\live_safety_test.py
$code=$LASTEXITCODE
if ($code -ne 0) {
    Write-Host "Expected remaining blocker may be MT5 Algo Trading OFF." -ForegroundColor Yellow
    exit $code
}
Write-Host "RESULT: READY FOR FINAL LIVE ACTION" -ForegroundColor Green
