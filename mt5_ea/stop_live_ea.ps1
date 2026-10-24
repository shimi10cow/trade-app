# Stop the new live EA for one account kind: demo | live. Positions stay open with their server-side stop-loss.
param([string]$Kind = "demo")
$pidFile = Join-Path $env:USERPROFILE ("TradeEA_data\live_{0}.pid" -f $Kind)
$p = $null
if (Test-Path $pidFile) {
    $p = Get-CimInstance Win32_Process -Filter ("ProcessId={0}" -f ((Get-Content $pidFile -Raw).Trim())) -ErrorAction SilentlyContinue
}
if (-not $p -or $p.CommandLine -notmatch 'start_live_ea\.ps1') { Write-Host ("The {0} EA is not running." -f $Kind) -ForegroundColor Yellow; exit 0 }
taskkill /T /F /PID $p.ProcessId | Out-Null     # the launcher and the Python EA under it
Remove-Item $pidFile -ErrorAction SilentlyContinue
Write-Host ("The {0} EA stopped. Open positions keep their stop-loss on the MT5 server." -f $Kind) -ForegroundColor Green
