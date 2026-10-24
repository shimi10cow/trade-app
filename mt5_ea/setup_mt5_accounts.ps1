$ErrorActionPreference = "Stop"
$source = "C:\Program Files\XMTrading MT5"
$root = Join-Path $env:LOCALAPPDATA "TradeTrackerMT5"
$repoDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# Account numbers live only on this PC (mt5_accounts.local.txt, not uploaded to GitHub).
# One account per line: <login> <server>   e.g.  12345678 XMTrading-MT5 3
# The first run asks for them and saves the file.
$listPath = Join-Path $repoDir "mt5_accounts.local.txt"
if (!(Test-Path $listPath)) {
  Write-Host "Enter the import accounts, one per line as: <login> <server>  (empty line to finish)"
  $lines = @()
  while ($true) { $l = Read-Host "account"; if ([string]::IsNullOrWhiteSpace($l)) { break }; $lines += $l.Trim() }
  if (!$lines.Count) { throw "No accounts entered" }
  $lines | Set-Content -Encoding UTF8 $listPath
}
$accounts = @()
foreach ($l in (Get-Content $listPath)) {
  $l = $l.Trim(); if (!$l -or $l.StartsWith("#")) { continue }
  $i = $l.IndexOf(" "); if ($i -lt 1) { throw "Bad line in ${listPath}: $l" }
  $accounts += @{ login = $l.Substring(0, $i); server = $l.Substring($i + 1).Trim() }
}

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
Write-Host "Opening $($accounts.Count) dedicated MT5 terminals."
Write-Host "Log each window into the account shown below and tick Save password."
Write-Host "DO NOT change the account of the EA terminal."
Write-Host ""

foreach ($a in $accounts) {
  $terminal = Join-Path (Join-Path $root $a.login) "terminal64.exe"
  Write-Host "$($a.login)  $($a.server)"
  Start-Process -FilePath $terminal
  Start-Sleep -Milliseconds 800
}

Write-Host ""
Write-Host "After all terminals are logged in, close this message only; terminals may stay open."
