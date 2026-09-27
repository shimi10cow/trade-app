$ErrorActionPreference = "Stop"
$env:EA_GAS_URL = "https://script.google.com/macros/s/AKfycbyTs-c4RGDRF-Z6CXNH7FJHE7wHBvtQhA7XkdLhncL3ubDBW6cIhbykW6B_rO2Tm83n/exec"
$env:EA_DRY_RUN = "true"
$env:EA_PAIRS = "EURUSD,USDJPY,EURJPY,AUDJPY,XAUUSD"
$env:EA_POLL_SEC = "2"
$env:EA_MAGIC = "560001"

# Fast daily startup: main.py is fail-closed until the cached/background GAS runtime is healthy.
# Full diagnostics belong to verify_dry_run.ps1 and are not repeated on every PC startup.
Write-Host "Hybrid EA - FAST DRY RUN (NO ORDERS)" -ForegroundColor Green
py .\main.py
