# Start the demo EA automatically when this Windows user logs on (1 minute after, window minimized). Run once.
#   setup_live_ea_autostart.ps1           -> turn on
#   setup_live_ea_autostart.ps1 -Remove   -> turn off
param([string]$Kind = "demo", [switch]$Remove)
$ErrorActionPreference = "Stop"
$name = "TradeEA live $Kind"
if ($Remove) {
    Unregister-ScheduledTask -TaskName $name -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Autostart off: $name" -ForegroundColor Yellow; exit 0
}
$bat = Join-Path $PSScriptRoot ("START_LIVE_EA_{0}.bat" -f $(if ($Kind -eq "live") { "REAL" } else { "DEMO" }))
$action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument ("/c start `"TradeEA`" /min `"{0}`"" -f $bat) -WorkingDirectory $PSScriptRoot
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$trigger.Delay = "PT1M"                                   # wait for the network and MT5's own start-up
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit ([TimeSpan]::Zero)
Register-ScheduledTask -TaskName $name -Action $action -Trigger $trigger -Settings $settings -Description "Starts the new live EA ($Kind) at logon" -Force | Out-Null
Write-Host "Autostart on: $name (1 minute after logon)" -ForegroundColor Green
