$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
Write-Host "Starting MT5 import worker (READ ONLY)..." -ForegroundColor Cyan
$running = Get-CimInstance Win32_Process -Filter "Name = 'python.exe' OR Name = 'py.exe'" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -match 'mt5_import_worker\.py' }
if ($running) { Write-Host "MT5 import worker is already running." -ForegroundColor DarkGray; exit 0 }
Start-Process -FilePath "py" -ArgumentList ".\mt5_import_worker.py" -WorkingDirectory $PSScriptRoot -WindowStyle Minimized
Write-Host "MT5 import worker started. It cannot place/close orders or modify SL/TP." -ForegroundColor Green
