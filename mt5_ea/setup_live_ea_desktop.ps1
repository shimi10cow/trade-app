# Put start / stop buttons for the new live EA (demo) on the desktop. Run once (again after moving the folder).
$ErrorActionPreference = "Stop"
$desktop = [Environment]::GetFolderPath("Desktop")
$ws = New-Object -ComObject WScript.Shell
$here = $PSScriptRoot
@(
  @{Name="新EA デモ START"; Target=(Join-Path $here "START_LIVE_EA_DEMO.bat"); Icon="%SystemRoot%\System32\shell32.dll,137"},
  @{Name="新EA デモ STOP";  Target=(Join-Path $here "STOP_LIVE_EA_DEMO.bat");  Icon="%SystemRoot%\System32\shell32.dll,131"},
  @{Name="新EA デモ 更新";  Target=(Join-Path $here "UPDATE_LIVE_EA_DEMO.bat"); Icon="%SystemRoot%\System32\shell32.dll,238"}
) | ForEach-Object {
  $lnk = $ws.CreateShortcut((Join-Path $desktop ($_.Name + ".lnk")))
  $lnk.TargetPath = $_.Target
  $lnk.WorkingDirectory = $here
  $lnk.IconLocation = $_.Icon
  $lnk.Save()
}
Write-Host "Desktop buttons created: 新EA デモ START / STOP" -ForegroundColor Green
