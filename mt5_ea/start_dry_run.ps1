$ErrorActionPreference = "Stop"
$env:EA_GAS_URL = "https://script.google.com/macros/s/AKfycbyTs-c4RGDRF-Z6CXNH7FJHE7wHBvtQhA7XkdLhncL3ubDBW6cIhbykW6B_rO2Tm83n/exec"
$env:EA_DRY_RUN = "true"
$env:EA_PAIRS = "EURUSD,USDJPY,EURJPY,AUDJPY,XAUUSD"
$env:EA_POLL_SEC = "2"
$env:EA_MAGIC = "560001"

Write-Host "Hybrid EA - local preflight (NO ORDERS)" -ForegroundColor Cyan
python .\preflight.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
python .\strategy_tests.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "Hybrid EA - runtime validation (NO ORDERS)" -ForegroundColor Cyan
python .\runtime_check.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Hybrid EA - connection test (NO ORDERS)" -ForegroundColor Cyan
python .\connection_test.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "Connection test passed. Starting DRY RUN..." -ForegroundColor Green
python .\main.py
