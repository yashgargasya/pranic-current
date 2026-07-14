# Stop every running Pranic Current daemon.
# The exclusive lock (pranic.lock) is released automatically when the process
# exits, so there is nothing else to clean up.

$ErrorActionPreference = "Stop"

$procs = Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
         Where-Object { $_.CommandLine -match 'pranic' }

if (-not $procs) {
    Write-Host "No pranic daemon running." -ForegroundColor Cyan
    return
}

$procs | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
Start-Sleep -Milliseconds 500

$left = Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
        Where-Object { $_.CommandLine -match 'pranic' }
if ($left) {
    Write-Host "STILL RUNNING: PID $($left.ProcessId -join ', ')" -ForegroundColor Red
} else {
    Write-Host "Stopped $($procs.Count) pranic process(es)." -ForegroundColor Green
}
