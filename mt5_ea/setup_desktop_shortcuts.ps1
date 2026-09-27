$ErrorActionPreference = "Stop"
$desktop=[Environment]::GetFolderPath("Desktop")
$here=$PSScriptRoot
$ws=New-Object -ComObject WScript.Shell
@(
  @{Name="EA START"; Target=(Join-Path $here "EA_START.bat"); Icon="%SystemRoot%\System32\shell32.dll,137"},
  @{Name="EA STOP"; Target=(Join-Path $here "EA_STOP.bat"); Icon="%SystemRoot%\System32\shell32.dll,131"}
) | ForEach-Object {
  $lnk=$ws.CreateShortcut((Join-Path $desktop ($_.Name+".lnk")))
  $lnk.TargetPath=$_.Target
  $lnk.WorkingDirectory=$here
  $lnk.IconLocation=$_.Icon
  $lnk.Save()
}
Write-Host "Desktop shortcuts created: EA START / EA STOP" -ForegroundColor Green
