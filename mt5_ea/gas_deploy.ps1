# GAS deploy (2026-11-21): GitHub main -> Apps Script -> the existing deployment gets a new version (the URL stays the same).
# Only the 3 files from GitHub are replaced; any other file in the Apps Script project is kept. The 3 old files are backed up first.
# Does not touch the program folder (reads main with git show), so the running EA is not affected.
$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSScriptRoot
$data = Join-Path $env:USERPROFILE "TradeEA_data"
$work = Join-Path $data "gas_clasp"
$cfgF = Join-Path $data "gas_deploy.json"
if (-not (Test-Path $cfgF) -or -not (Test-Path (Join-Path $work ".clasp.json"))) { throw "先に GAS_DEPLOY_SETUP.bat を 1 回実行してください" }
$cfg = Get-Content $cfgF -Raw -Encoding UTF8 | ConvertFrom-Json
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"

Write-Host "1/5 GitHub の main を確認" -ForegroundColor Cyan
git -C $repo fetch -q origin main
if ($LASTEXITCODE -ne 0) { throw "git fetch failed" }
$commit = (git -C $repo log -1 --format="%h %s" origin/main)
Write-Host "   main: $commit"

Write-Host "2/5 Apps Script の今の中身を読む（控えを取る）" -ForegroundColor Cyan
Push-Location $work
try {
    clasp pull; if ($LASTEXITCODE -ne 0) { throw "clasp pull failed" }
    # 2026-11-22: backups live OUTSIDE the clasp folder (clasp push sent backup\*.js too -> "already declared", GAS stopped)
    $bk = Join-Path $data ("gas_backup\" + $stamp); New-Item -ItemType Directory -Force -Path $bk | Out-Null
    Set-Content -Path (Join-Path $work ".claspignore") -Value "backup/**`r`nnode_modules/**" -Encoding ASCII
    foreach ($p in $cfg.map.PSObject.Properties) { Copy-Item (Join-Path $work $p.Value) $bk -ErrorAction SilentlyContinue }

    Write-Host "3/5 main のファイルに置き換える" -ForegroundColor Cyan
    foreach ($p in $cfg.map.PSObject.Properties) {
        $dst = Join-Path $work $p.Value
        cmd /c ("git -C `"{0}`" show origin/main:{1} > `"{2}`"" -f $repo, $p.Name, $dst)
        if ($LASTEXITCODE -ne 0 -or (Get-Item $dst).Length -lt 1000) { throw "main から $($p.Name) を読めませんでした" }
        Write-Host ("   {0} -> {1}" -f $p.Name, $p.Value)
    }

    Write-Host "4/5 Apps Script に送る（clasp push）" -ForegroundColor Cyan
    clasp push -f; if ($LASTEXITCODE -ne 0) { throw "clasp push failed（控え: $bk）" }

    Write-Host "5/5 今のデプロイを新しいバージョンに（URL はそのまま）" -ForegroundColor Cyan
    clasp deploy -i $cfg.deploymentId -d ("auto " + $stamp + " " + $commit.Substring(0, [Math]::Min(60, $commit.Length)))
    if ($LASTEXITCODE -ne 0) { throw "clasp deploy failed" }
} finally { Pop-Location }
Add-Content -Path (Join-Path $data "gas_deploy.log") -Value ("{0} {1}" -f $stamp, $commit) -Encoding UTF8
Write-Host ""
Write-Host "GAS を更新しました（$commit）。アプリを開き直すと新しい GAS で動きます。" -ForegroundColor Green
