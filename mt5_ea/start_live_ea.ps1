# Start the new live EA for one account kind (demo | live) and keep it running (2026-10-24).
# This window is the watcher: it restarts the EA if it stops, restarts MT5 if MT5 closes, and keeps the PC awake.
# Closing this window (or STOP_LIVE_EA_*.bat) stops the EA. Open positions keep their stop-loss on the MT5 server.
param([string]$Kind = "demo")
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)        # repository folder (mt5_ea's parent)
$Host.UI.RawUI.WindowTitle = "新EA ($Kind) - このウィンドウを閉じると EA が止まります"
$env:EA_ACCOUNT_KIND = $Kind
if ($Kind -eq "live") { $env:EA_LIVE_LOGIN = $env:EA_REAL_LOGIN; $env:EA_MT5_PATH = $env:EA_REAL_MT5_PATH }
else { $env:EA_LIVE_LOGIN = $env:EA_DEMO_LOGIN; $env:EA_MT5_PATH = $env:EA_DEMO_MT5_PATH }
if (-not $env:EA_GAS_URL -or -not $env:EA_GAS_KEY) { throw "Run CONFIGURE_LIVE_EA.bat first." }

# EA records live OUTSIDE the program folder, so replacing the program never loses them
$data = Join-Path $env:USERPROFILE "TradeEA_data"
New-Item -ItemType Directory -Force -Path $data | Out-Null

# Refuse a second copy for the same account kind (two copies would place every order twice)
$pidFile = Join-Path $data ("live_{0}.pid" -f $Kind)
if (Test-Path $pidFile) {
    $old = Get-CimInstance Win32_Process -Filter ("ProcessId={0}" -f ((Get-Content $pidFile -Raw).Trim())) -ErrorAction SilentlyContinue
    if ($old -and $old.CommandLine -match 'start_live_ea\.ps1') { throw ("The {0} EA is already running (PID {1}). Stop it first." -f $Kind, $old.ProcessId) }
}
Set-Content -Path $pidFile -Value $PID

$env:EA_STATE_FILE = Join-Path $data ("live_state_{0}.json" -f $Kind)
$env:EA_CONFIG_FILE = Join-Path $data ("live_config_{0}.json" -f $Kind)
$env:EA_OUTBOX_DB = Join-Path $data ("live_outbox_{0}.sqlite3" -f $Kind)
$env:EA_LOG_FILE = Join-Path $data ("live_{0}.log" -f $Kind)
$env:PYTHONIOENCODING = "utf-8"
$watchLog = Join-Path $data ("watcher_{0}.log" -f $Kind)

function Say([string]$text, [string]$color = "Gray") {
    $line = "{0} {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $text
    Write-Host $line -ForegroundColor $color
    Add-Content -Path $watchLog -Value $line -Encoding UTF8
}

# Keep old logs small: move a log over 20 MB aside (one old copy is kept)
foreach ($f in @($env:EA_LOG_FILE, $watchLog)) {
    if ((Test-Path $f) -and (Get-Item $f).Length -gt 20MB) { Move-Item $f ($f + ".1") -Force }
}

# Keep the PC from going to sleep while this window is open (the screen may still turn off)
Add-Type -Namespace TradeEA -Name Power -MemberDefinition '[DllImport("kernel32.dll")] public static extern uint SetThreadExecutionState(uint f);'
[void][TradeEA.Power]::SetThreadExecutionState([uint32]"0x80000001")   # ES_CONTINUOUS | ES_SYSTEM_REQUIRED

$mt5Exe = if ($env:EA_MT5_PATH) { $env:EA_MT5_PATH } else { "C:\Program Files\XMTrading MT5\terminal64.exe" }
function Mt5Running { [bool](Get-Process terminal64 -ErrorAction SilentlyContinue | Where-Object { $_.Path -eq $mt5Exe }) }
function Ensure-Mt5 {
    if (Mt5Running) { return }
    Say "MT5 is not running: starting it" Yellow
    Start-Process explorer.exe -ArgumentList "`"$mt5Exe`""   # started through explorer so STOP never closes MT5
    for ($i = 0; $i -lt 24 -and -not (Mt5Running); $i++) { Start-Sleep 5 }
    Start-Sleep 30                                            # let it log in and load prices
}

# One-time check before starting: right account, connected, Algo Trading on
function Check-Mt5 {
    $code = @"
import os, MetaTrader5 as m
p = os.environ.get('EA_MT5_PATH') or None
if not (m.initialize(p) if p else m.initialize()): print('NG MT5 not reachable:', m.last_error()); raise SystemExit
a, t = m.account_info(), m.terminal_info()
want = os.environ.get('EA_LIVE_LOGIN', '')
print(('OK' if a and str(a.login) == want else 'NG'), 'account', a.login if a else None, 'want', want)
print(('OK' if t.connected else 'NG'), 'connected to the server' if t.connected else 'not connected to the server')
print(('OK' if t.trade_allowed else 'NG'), 'Algo Trading is ON' if t.trade_allowed else 'Algo Trading is OFF: press the Algo Trading button in MT5 or no order can be placed')
"@
    try {
        $ErrorActionPreference = "Continue"
        $out = $code | py - 2>&1
        foreach ($l in $out) { Say ("check: " + $l) ($(if ("$l" -like "OK*") { "Green" } else { "Red" })) }
    } catch { Say ("check failed: " + $_) Red }
}

Say ("Live EA ({0}) account {1}: watcher started" -f $Kind, $env:EA_LIVE_LOGIN) Green
Ensure-Mt5
Check-Mt5

$wait = 30
while ($true) {
    Ensure-Mt5
    Say "starting the EA" Cyan
    $started = Get-Date; $mt5Closed = $false
    $ea = Start-Process py -ArgumentList "-m", "mt5_ea.live.main_live" -NoNewWindow -PassThru
    $null = $ea.Handle                                        # keep the handle so the exit code can be read later
    while (-not $ea.HasExited) {
        Start-Sleep 20
        if (-not (Mt5Running)) {
            Say "MT5 closed: restarting MT5 and the EA" Yellow
            taskkill /T /F /PID $ea.Id | Out-Null
            $mt5Closed = $true
            break
        }
    }
    $ea.WaitForExit(10000) | Out-Null
    if ($mt5Closed) { continue }                              # restart MT5 right away (top of the loop)
    $code = if ($ea.HasExited) { $ea.ExitCode } else { "?" }
    # A run that lasted over 10 minutes resets the wait; quick failures wait longer each time (up to 5 minutes)
    if (((Get-Date) - $started).TotalMinutes -gt 10) { $wait = 30 } else { $wait = [Math]::Min($wait * 2, 300) }
    Say ("the EA stopped (exit {0}): starting again in {1} s" -f $code, $wait) Yellow
    Start-Sleep $wait
}
