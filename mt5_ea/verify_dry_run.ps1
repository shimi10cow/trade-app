$ErrorActionPreference = "Stop"
$env:EA_GAS_URL = "https://script.google.com/macros/s/AKfycbyTs-c4RGDRF-Z6CXNH7FJHE7wHBvtQhA7XkdLhncL3ubDBW6cIhbykW6B_rO2Tm83n/exec"
$env:EA_DRY_RUN = "true"
$env:EA_PAIRS = "EURUSD,USDJPY,EURJPY,AUDJPY,XAUUSD"
$env:EA_POLL_SEC = "2"
$env:EA_MAGIC = "560001"

Write-Host "Hybrid EA - FULL VERIFICATION (NO ORDERS)" -ForegroundColor Cyan
py .\preflight.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
py .\strategy_tests.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
py .\runtime_check.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
py .\connection_test.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "RESULT: FULL VERIFICATION PASS" -ForegroundColor Green
