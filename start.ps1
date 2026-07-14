# Start a single Pranic Current daemon in the background.
# It runs detached, so this terminal stays free and closing it will NOT stop
# the daemon. Output goes to pranic.out.log / pranic.err.log.
#
# The daemon takes an exclusive lock (pranic.lock); if one is already running,
# it refuses to start a second rather than double-sending. Run stop.ps1 first
# if you want to replace a running instance.

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

$running = Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
           Where-Object { $_.CommandLine -match 'pranic' }
if ($running) {
    Write-Host "A pranic daemon is already running (PID $($running.ProcessId -join ', '))." -ForegroundColor Yellow
    Write-Host "Run .\stop.ps1 first if you want to restart it." -ForegroundColor Yellow
    return
}

$proc = Start-Process -FilePath "$PSScriptRoot\.venv\Scripts\python.exe" `
    -ArgumentList "-m", "pranic_current", "run" `
    -WorkingDirectory $PSScriptRoot `
    -WindowStyle Hidden `
    -RedirectStandardOutput "$PSScriptRoot\pranic.out.log" `
    -RedirectStandardError  "$PSScriptRoot\pranic.err.log" `
    -PassThru

Write-Host "Started pranic daemon in the background (PID $($proc.Id))." -ForegroundColor Green
Write-Host "Logs: pranic.err.log (daemon activity), pranic.out.log" -ForegroundColor Cyan
Write-Host "Stop it any time with .\stop.ps1. This terminal is free to use." -ForegroundColor Cyan
