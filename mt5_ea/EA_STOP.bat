@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$procs = Get-CimInstance Win32_Process | Where-Object { ($_.Name -match '^(python|pythonw)\.exe$' -and $_.CommandLine -match 'main\.py') -or ($_.Name -match '^powershell\.exe$' -and $_.CommandLine -match 'start_live\.ps1') }; if(-not $procs){ Write-Host 'EA is not running.' -ForegroundColor Yellow; exit 0 }; $ids=@($procs.ProcessId); foreach($p in $procs){ try { Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue } catch {} }; Write-Host ('EA stopped. PID: ' + ($ids -join ', ')) -ForegroundColor Green"
timeout /t 2 /nobreak >nul
