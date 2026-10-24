# Put start / stop buttons for the new live EA (demo) on the desktop. Run once (again after moving the folder).
$ErrorActionPreference = "Stop"
$desktop = [Environment]::GetFolderPath("Desktop")
$ws = New-Object -ComObject WScript.Shell
$here = $PSScriptRoot
@(
  @{Name="新EA デモ START"; Target=(Join-Path $here "START_LIVE_EA_DEMO.bat"); Icon="%SystemRoot%\System32\shell32.dll,137"},
  @{Name="新EA デモ STOP";  Target=(Join-Path $here "STOP_LIVE_EA_DEMO.bat");  Icon="%SystemRoot%\System32\shell32.dll,131"},
  @{Name="新EA リアル START"; Target=(Join-Path $here "START_LIVE_EA_REAL.bat"); Icon="%SystemRoot%\System32\shell32.dll,77"},
  @{Name="新EA リアル STOP";  Target=(Join-Path $here "STOP_LIVE_EA_REAL.bat");  Icon="%SystemRoot%\System32\shell32.dll,131"},
  @{Name="新EA 更新";  Target=(Join-Path $here "UPDATE_LIVE_EA.bat"); Icon="%SystemRoot%\System32\shell32.dll,238"},
  @{Name="EA用 MT5 リアル";  Target=[Environment]::GetEnvironmentVariable("EA_REAL_MT5_PATH","User"); Icon=""}
) | Where-Object { $_.Target } | ForEach-Object {
  $lnk = $ws.CreateShortcut((Join-Path $desktop ($_.Name + ".lnk")))
  $lnk.TargetPath = $_.Target
  $lnk.WorkingDirectory = $here
  if ($_.Icon) { $lnk.IconLocation = $_.Icon }
  $lnk.Save()
}
Remove-Item (Join-Path $desktop "新EA デモ 更新.lnk") -ErrorAction SilentlyContinue   # replaced by 新EA 更新 (demo + real)
Write-Host "Desktop buttons created: 新EA デモ / リアル START・STOP, 新EA 更新, EA用 MT5 リアル" -ForegroundColor Green
