$ErrorActionPreference = "Stop"
$source = "C:\Program Files\XMTrading MT5"
$root = Join-Path $env:LOCALAPPDATA "TradeTrackerMT5"
$repoDir = Split-Path -Parent $MyInvocation.MyCommand.Path

$accounts = @(
  @{ login="72124321";  server="XMTrading-MT5 3" },
  @{ login="70066643";  server="XMTrading-MT5 3" },
  @{ login="370286831"; server="XMTrading-MT5 2" },
  @{ login="72313599";  server="XMTrading-MT5 3" },
  @{ login="370090754"; server="XMTrading-MT5 2" },
  @{ login="370299550"; server="XMTrading-MT5 2" },
  @{ login="72010266";  server="XMTrading-MT5 3" },
  @{ login="370299556"; server="XMTrading-MT5 2" }
)

if (!(Test-Path (Join-Path $source "terminal64.exe"))) {
  throw "XM MT5 not found: $source"
}
New-Item -ItemType Directory -Force -Path $root | Out-Null

$config = @{ accounts = @() }
foreach ($a in $accounts) {
  $dest = Join-Path $root $a.login
  if (!(Test-Path (Join-Path $dest "terminal64.exe"))) {
    Write-Host "Creating MT5 copy for $($a.login) ..."
    New-Item -ItemType Directory -Force -Path $dest | Out-Null
    Copy-Item -Path (Join-Path $source "*") -Destination $dest -Recurse -Force
  }
  $terminal = Join-Path $dest "terminal64.exe"
  $config.accounts += @{
    name = "manual-$($a.login)"
    enabled = $true
    terminalPath = $terminal
    login = $a.login
    server = $a.server
  }
}

$configPath = Join-Path $repoDir "mt5_accounts.json"
$config | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 $configPath
Write-Host ""
Write-Host "Created: $configPath"
Write-Host "Opening 8 dedicated MT5 terminals."
Write-Host "Log each window into the account shown below and tick Save password."
Write-Host "DO NOT change the primary EA terminal account: 370102382 / XMTrading-MT5 2"
Write-Host ""

foreach ($a in $accounts) {
  $terminal = Join-Path (Join-Path $root $a.login) "terminal64.exe"
  Write-Host "$($a.login)  $($a.server)"
  Start-Process -FilePath $terminal
  Start-Sleep -Milliseconds 800
}

Write-Host ""
Write-Host "After all 8 terminals are logged in, close this message only; terminals may stay open."
