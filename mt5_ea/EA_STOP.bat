@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$procs = Get-CimInstance Win32_Process | Where-Object { $_.Name -match '^(python|pythonw|py)\\.exe$' -and $_.CommandLine -match '(^|[\\/])main\\.py( |$)' -and $_.CommandLine -match 'trade_app' }; if(-not $procs){ Write-Host 'EA is not running.' -ForegroundColor Yellow; exit 0 }; foreach($p in $procs){ Stop-Process -Id $p.ProcessId -Force }; Write-Host 'EA stopped.' -ForegroundColor Green"
pause
