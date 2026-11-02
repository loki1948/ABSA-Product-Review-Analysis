# Stops this project's backend (uvicorn) and frontend (Vite) dev servers.
# Usage:  powershell -ExecutionPolicy Bypass -File scripts\stop_app.ps1

$ErrorActionPreference = 'Stop'

function Get-ListenerPids([int[]]$Ports) {
    # netstat is used instead of Get-NetTCPConnection, which returned nothing on
    # this machine while a server was still listening.
    $found = @()
    foreach ($line in (netstat -ano -p tcp) + (netstat -ano -p tcpv6)) {
        if ($line -match '^\s*TCP\s+\S+:(\d+)\s+\S+\s+LISTENING\s+(\d+)\s*$') {
            if ($Ports -contains [int]$Matches[1]) { $found += [int]$Matches[2] }
        }
    }
    $found | Sort-Object -Unique
}

$root = Split-Path -Parent $PSScriptRoot
$escapedRoot = [regex]::Escape($root)
$stopped = 0

# 1. This project's uvicorn (run by .venv's python) and Vite (from frontend\node_modules).
#    When they exit, their "npm run dev" / cmd parents exit or sit idle.
$procs = Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -and (
        ($_.CommandLine -match 'uvicorn\s+app\.main:app' -and $_.CommandLine -match "$escapedRoot\\\.venv") -or
        ($_.CommandLine -match "$escapedRoot\\frontend\\node_modules\\.*vite")
    )
}
foreach ($p in $procs) {
    try { Stop-Process -Id $p.ProcessId -Force; $stopped++ } catch { }
}

# 2. Whatever still listens on the app's ports, if it is python or node.
foreach ($procId in Get-ListenerPids @(8000, 5173)) {
    $proc = Get-Process -Id $procId -ErrorAction SilentlyContinue
    if ($proc -and $proc.ProcessName -in @('python', 'node')) {
        try { Stop-Process -Id $procId -Force; $stopped++ } catch { }
    } elseif ($proc) {
        Write-Warning "Port in use by $($proc.ProcessName) (PID $procId); not stopping it."
    }
}

Start-Sleep -Seconds 1
$left = Get-ListenerPids @(8000, 5173)
if ($left) {
    Write-Warning "Ports still in use by PID(s): $($left -join ', ')"
    exit 1
}
Write-Host "Stopped $stopped process(es). Ports 8000 and 5173 are free." -ForegroundColor Green
