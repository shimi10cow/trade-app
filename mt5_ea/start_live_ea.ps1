# Start the new live EA for one account kind: demo | live  (2026-10-24)
param([string]$Kind = "demo")
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)        # repository folder (mt5_ea's parent)
$env:EA_ACCOUNT_KIND = $Kind
if ($Kind -eq "live") { $env:EA_LIVE_LOGIN = $env:EA_REAL_LOGIN; $env:EA_MT5_PATH = $env:EA_REAL_MT5_PATH }
else { $env:EA_LIVE_LOGIN = $env:EA_DEMO_LOGIN; $env:EA_MT5_PATH = $env:EA_DEMO_MT5_PATH }
# EA records live OUTSIDE the program folder, so replacing the program (new ZIP) never loses them
$data = Join-Path $env:USERPROFILE "TradeEA_data"
New-Item -ItemType Directory -Force -Path $data | Out-Null
$env:EA_STATE_FILE = Join-Path $data ("live_state_{0}.json" -f $Kind)
$env:EA_CONFIG_FILE = Join-Path $data ("live_config_{0}.json" -f $Kind)
$env:EA_OUTBOX_DB = Join-Path $data ("live_outbox_{0}.sqlite3" -f $Kind)
$env:EA_LOG_FILE = Join-Path $data ("live_{0}.log" -f $Kind)
if (-not $env:EA_GAS_URL -or -not $env:EA_GAS_KEY) { throw "Run configure_live_ea.ps1 first." }
Write-Host ("Live EA ({0}) account {1}" -f $Kind, $env:EA_LIVE_LOGIN) -ForegroundColor Green
py -m mt5_ea.live.main_live
