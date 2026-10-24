# MT5 import from the desktop button (2026-10-25): runs mt5_ea.live.importer in the repository folder.
# Opens the one import MT5, switches through the accounts in TradeEA_data\import_accounts.json, sends the deals to the app, closes it.
# Output goes to this window and to TradeEA_data\import.log.   -Reread90: read the last 90 days again.
param([switch]$Reread90)
$ErrorActionPreference = "Continue"
Set-Location (Split-Path -Parent $PSScriptRoot)        # repository folder (mt5_ea's parent)
if (-not $env:EA_GAS_URL -or -not $env:EA_GAS_KEY) { Write-Host "Run CONFIGURE_LIVE_EA.bat first (EA_GAS_URL / EA_GAS_KEY)." -ForegroundColor Red; exit 1 }
$data = Join-Path $env:USERPROFILE "TradeEA_data"
New-Item -ItemType Directory -Force -Path $data | Out-Null
if (-not (Test-Path (Join-Path $data "import_accounts.json"))) { Write-Host "TradeEA_data\import_accounts.json is missing." -ForegroundColor Red; exit 1 }
$log = Join-Path $data "import.log"

# One import at a time (two would fight over the same import MT5)
$pidFile = Join-Path $data "import.pid"
if (Test-Path $pidFile) {
    $old = Get-CimInstance Win32_Process -Filter ("ProcessId={0}" -f ((Get-Content $pidFile -Raw).Trim())) -ErrorAction SilentlyContinue
    if ($old -and $old.CommandLine -match 'run_import\.ps1') { Write-Host "An import is already running (PID $($old.ProcessId))." -ForegroundColor Yellow; exit 1 }
}
Set-Content -Path $pidFile -Value $PID

$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [Text.Encoding]::UTF8      # read Python's UTF-8 output as UTF-8 (Japanese messages)
$args_ = if ($Reread90) { "--reread90" } else { "" }
$head = "{0} ===== import start{1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $(if ($Reread90) { " (reread 90 days)" } else { "" })
Write-Host $head -ForegroundColor Cyan; Add-Content -Path $log -Value $head -Encoding UTF8
# cmd merges Python's log (stderr) into stdout, so PowerShell gets plain lines
cmd /c "py -m mt5_ea.live.importer $args_ 2>&1" | ForEach-Object {
    $l = "$_"
    $color = if ($l -match 'ERROR|failed|Traceback') { "Red" } elseif ($l -match 'GAS:|import:') { "Green" } else { "Gray" }
    Write-Host $l -ForegroundColor $color
    Add-Content -Path $log -Value $l -Encoding UTF8
}
$code = $LASTEXITCODE
$tail = "{0} ===== import end (exit {1})" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $code
Write-Host $tail -ForegroundColor $(if ($code -eq 0) { "Cyan" } else { "Red" }); Add-Content -Path $log -Value $tail -Encoding UTF8
Remove-Item $pidFile -ErrorAction SilentlyContinue
exit $code
