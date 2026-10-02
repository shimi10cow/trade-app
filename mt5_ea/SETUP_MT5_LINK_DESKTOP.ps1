$ErrorActionPreference = "Stop"
$desktop = [Environment]::GetFolderPath("Desktop")
$ws = New-Object -ComObject WScript.Shell
$base = $PSScriptRoot
$items = @(
  @{Name="MT5連携 START"; Target=(Join-Path $base "MT5_LINK_START.bat"); Icon="%SystemRoot%\System32\shell32.dll,167"},
  @{Name="MT5連携 STOP";  Target=(Join-Path $base "MT5_LINK_STOP.bat");  Icon="%SystemRoot%\System32\shell32.dll,131"}
)
foreach($item in $items){
  $lnk=$ws.CreateShortcut((Join-Path $desktop ($item.Name+".lnk")))
  $lnk.TargetPath=$item.Target
  $lnk.WorkingDirectory=$base
  $lnk.IconLocation=$item.Icon
  $lnk.Save()
}
Write-Host "Desktop shortcuts created: MT5連携 START / STOP" -ForegroundColor Green
