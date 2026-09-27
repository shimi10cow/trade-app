param(
    [Parameter(Mandatory=$true)][string]$Login,
    [Parameter(Mandatory=$true)][string]$Server
)
$ErrorActionPreference = "Stop"
# Store only on this PC/user profile. Never commit account identity to Git.
[Environment]::SetEnvironmentVariable("EA_LIVE_LOGIN",$Login,"User")
[Environment]::SetEnvironmentVariable("EA_LIVE_SERVER",$Server,"User")
[Environment]::SetEnvironmentVariable("EA_LIVE_ARMED","false","User")
$env:EA_LIVE_LOGIN=$Login
$env:EA_LIVE_SERVER=$Server
$env:EA_LIVE_ARMED="false"
Write-Host "LIVE account lock saved locally; LIVE remains DISARMED." -ForegroundColor Yellow
py .\live_safety_test.py
