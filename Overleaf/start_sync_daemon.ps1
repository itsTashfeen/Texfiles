# Start the Overleaf two-way sync daemon hidden (no CMD window).
# Usage:
#   powershell -ExecutionPolicy Bypass -File .\start_sync_daemon.ps1

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent (Split-Path -Parent $Root)
$Python = Join-Path $RepoRoot ".venv\Scripts\python.exe"
$Daemon = Join-Path $Root "sync_daemon.py"
$PidFile = Join-Path $Root "sync_daemon.pid"
$OutLog = Join-Path $Root "sync_daemon.out.log"
$ErrLog = Join-Path $Root "sync_daemon.err.log"

if (-not (Test-Path $Python)) {
    Write-Error "Python not found at $Python"
}

if (Test-Path $PidFile) {
    $existing = Get-Content $PidFile -ErrorAction SilentlyContinue
    if ($existing -and (Get-Process -Id $existing -ErrorAction SilentlyContinue)) {
        Write-Host "Daemon already running (PID $existing)."
        exit 0
    }
}

$proc = Start-Process `
    -FilePath $Python `
    -ArgumentList "`"$Daemon`"" `
    -WorkingDirectory $Root `
    -WindowStyle Hidden `
    -RedirectStandardOutput $OutLog `
    -RedirectStandardError $ErrLog `
    -PassThru

# sync_daemon.py also writes sync_daemon.pid; keep a fallback here.
$proc.Id | Set-Content -Path $PidFile -Encoding ascii
Write-Host "Started hidden sync daemon (PID $($proc.Id))."
Write-Host "Log: $(Join-Path $Root 'sync_daemon.log')"
