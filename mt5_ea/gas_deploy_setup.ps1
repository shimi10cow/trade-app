# GAS deploy, one-time setup (2026-11-21): installs clasp, logs in to Google, links the Apps Script project.
# After this, GAS_DEPLOY.bat sends Code.gs / gas/EA_Live.gs / gas/Trades.gs of GitHub main to Apps Script and updates the existing deployment (same URL).
$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
$data = Join-Path $env:USERPROFILE "TradeEA_data"
$work = Join-Path $data "gas_clasp"
$cfgF = Join-Path $data "gas_deploy.json"
function Step([string]$t) { Write-Host ""; Write-Host "== $t" -ForegroundColor Cyan }

Step "1/5 Node.js"
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Host "Node.js がありません。次の 1 行を実行してから、この窓を閉じて GAS_DEPLOY_SETUP.bat をもう一度:" -ForegroundColor Yellow
    Write-Host "  winget install OpenJS.NodeJS.LTS"
    exit 1
}
node -v

Step "2/5 clasp (Google's Apps Script command line, version 2.4.2)"
if (-not (Get-Command clasp -ErrorAction SilentlyContinue)) { npm install -g @google/clasp@2.4.2; if ($LASTEXITCODE -ne 0) { throw "npm install failed" } }
clasp -v

Step "3/5 Apps Script API"
Write-Host "ブラウザで開くページの「Google Apps Script API」をオンにしてください（1 回だけ）。オンにしたら Enter。" -ForegroundColor Yellow
Start-Process "https://script.google.com/home/usersettings"
Read-Host | Out-Null

Step "4/5 Google login (browser)"
clasp login
if ($LASTEXITCODE -ne 0) { throw "clasp login failed" }

Step "5/5 Link the Apps Script project"
Write-Host "Apps Script の画面 → 左の歯車「プロジェクトの設定」→「スクリプト ID」をコピーして貼り付け、Enter:" -ForegroundColor Yellow
$scriptId = (Read-Host "スクリプト ID").Trim()
if (-not $scriptId) { throw "no script id" }
if (Test-Path $work) { Rename-Item -Path $work -NewName ((Split-Path $work -Leaf) + "_old_" + (Get-Date -Format "yyyyMMdd_HHmmss")) }
New-Item -ItemType Directory -Force -Path $work | Out-Null
Push-Location $work
try { clasp clone $scriptId; if ($LASTEXITCODE -ne 0) { throw "clasp clone failed" } } finally { Pop-Location }

$files = Get-ChildItem $work -File | Where-Object { $_.Extension -in ".gs", ".js", ".html" } | ForEach-Object { $_.Name }
Write-Host "Apps Script のファイル: $($files -join ', ')"
$code = $files | Where-Object { $_ -match '^(Code|コード)\.(gs|js)$' } | Select-Object -First 1
$ea = $files | Where-Object { $_ -match '^EA_Live\.(gs|js)$' } | Select-Object -First 1
$tr = $files | Where-Object { $_ -match '^Trades\.(gs|js)$' } | Select-Object -First 1
if (-not $code -or -not $ea -or -not $tr) { throw "Code / EA_Live / Trades のどれかが見つかりません。名前をクラウドに伝えてください: $($files -join ', ')" }
$other = $files | Where-Object { $_ -notin @($code, $ea, $tr) }
if ($other) { Write-Host "GitHub に無いファイル（そのまま残す）: $($other -join ', ')" -ForegroundColor Yellow }

$dep = ""
if ($env:EA_GAS_URL -match '/macros/s/([^/]+)/exec') { $dep = $Matches[1] }
Write-Host ""
Push-Location $work; clasp deployments; Pop-Location
if ($dep) { Write-Host "EA が使っている URL のデプロイ ID: $dep" -ForegroundColor Green }
else { $dep = (Read-Host "上の一覧から、EA とアプリが使っているデプロイの ID（AKfy... で始まる長い方）").Trim() }
@{ scriptId = $scriptId; deploymentId = $dep; map = @{ "Code.gs" = $code; "gas/EA_Live.gs" = $ea; "gas/Trades.gs" = $tr } } | ConvertTo-Json | Set-Content -Path $cfgF -Encoding UTF8
Write-Host ""
Write-Host "設定できました: $cfgF" -ForegroundColor Green
Write-Host "これからは GAS_DEPLOY.bat をダブルクリックするだけで、GitHub の main の GAS が反映されます（URL はそのまま）。"
