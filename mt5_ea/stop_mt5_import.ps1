$ErrorActionPreference = "Stop"
$running = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { $_.Name -in @('python.exe','py.exe') -and $_.CommandLine -match 'mt5_import_worker\.py' }
if (-not $running) { exit 0 }
foreach ($p in $running) { Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue }
