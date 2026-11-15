# Stop the hidden Overleaf sync daemon.
# Usage:
#   powershell -ExecutionPolicy Bypass -File .\stop_sync_daemon.ps1

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$PidFile = Join-Path $Root "sync_daemon.pid"

if (-not (Test-Path $PidFile)) {
    Write-Host "No PID file found. Daemon does not appear to be running."
    exit 0
}

$pidValue = (Get-Content $PidFile -ErrorAction SilentlyContinue | Select-Object -First 1).Trim()
if (-not $pidValue) {
    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
    Write-Host "PID file was empty. Cleaned up."
    exit 0
}

$proc = Get-Process -Id $pidValue -ErrorAction SilentlyContinue
if ($null -eq $proc) {
    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
    Write-Host "Process $pidValue not found. Cleaned up PID file."
    exit 0
}

Stop-Process -Id $pidValue -Force
Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
Write-Host "Stopped sync daemon (PID $pidValue)."
