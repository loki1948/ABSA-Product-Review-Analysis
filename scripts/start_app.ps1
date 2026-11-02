# Starts the ABSA app: backend (FastAPI on :8000) then frontend (Vite on :5173).
# Usage (from the project folder, in PowerShell):
#   powershell -ExecutionPolicy Bypass -File scripts\start_app.ps1
#
# Each server gets its own console window so you can watch its log. The windows
# run under cmd.exe, so uvicorn's normal INFO lines (written to stderr) are not
# shown as PowerShell "NativeCommandError" errors. Close a window, or run
# scripts\stop_app.ps1, to stop the servers.

param(
    [switch]$NoBrowser,
    [int]$TimeoutSeconds = 240
)

$ErrorActionPreference = 'Stop'
$root     = Split-Path -Parent $PSScriptRoot
$backend  = Join-Path $root 'backend'
$frontend = Join-Path $root 'frontend'
$python   = Join-Path $root '.venv\Scripts\python.exe'

function Fail($msg) { Write-Host "ERROR: $msg" -ForegroundColor Red; exit 1 }

# --- Preflight checks -------------------------------------------------------
if (-not (Test-Path $python)) {
    Fail "No virtual environment at .venv. Run the README 'Backend environment' setup first."
}
foreach ($m in 'aspect_extraction', 'sentiment', 'overall_sentiment') {
    if (-not (Test-Path (Join-Path $root "models\$m"))) {
        Fail "Model folder models\$m is missing. See README (absa-models.zip)."
    }
}
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) { Fail 'npm not found. Install Node.js 20 or newer.' }
if (-not (Test-Path (Join-Path $frontend 'node_modules'))) {
    Write-Host 'Installing frontend packages (first run only)...' -ForegroundColor Yellow
    Push-Location $frontend
    try { cmd /c 'npm install' ; if ($LASTEXITCODE -ne 0) { Fail 'npm install failed.' } } finally { Pop-Location }
}

# --- Free the ports from any earlier run ------------------------------------
& (Join-Path $PSScriptRoot 'stop_app.ps1')
if ($LASTEXITCODE -ne 0) { Fail 'Ports 8000/5173 are still in use; close the program using them and retry.' }

function Wait-Url($url, $seconds, $check) {
    $deadline = (Get-Date).AddSeconds($seconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $r = Invoke-WebRequest $url -UseBasicParsing -TimeoutSec 3
            if (& $check $r) { return $true }
        } catch { }
        Start-Sleep -Seconds 2
    }
    return $false
}

# --- Backend ----------------------------------------------------------------
Write-Host 'Starting backend (loading models takes 10-60 s)...' -ForegroundColor Cyan
$backendCmd = "title ABSA backend :8000 && cd /d `"$backend`" && `"$python`" -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
Start-Process cmd.exe -ArgumentList '/k', $backendCmd -WorkingDirectory $backend | Out-Null

$ok = Wait-Url 'http://localhost:8000/api/health' $TimeoutSeconds {
    param($r) ($r.Content | ConvertFrom-Json).status -eq 'ok'
}
if (-not $ok) { Fail 'Backend did not become healthy. Read the "ABSA backend" window for the error.' }
Write-Host 'Backend healthy: http://localhost:8000/api' -ForegroundColor Green

# --- Frontend (only after the backend is up, so the proxy never sees ECONNREFUSED)
Write-Host 'Starting frontend...' -ForegroundColor Cyan
$frontendCmd = "title ABSA frontend :5173 && cd /d `"$frontend`" && npm run dev -- --port 5173 --strictPort"
Start-Process cmd.exe -ArgumentList '/k', $frontendCmd -WorkingDirectory $frontend | Out-Null

$ok = Wait-Url 'http://localhost:5173/api/health' 90 { param($r) $r.StatusCode -eq 200 }
if (-not $ok) { Fail 'Frontend did not start. Read the "ABSA frontend" window for the error.' }
Write-Host 'Frontend ready: http://localhost:5173' -ForegroundColor Green

if (-not $NoBrowser) { Start-Process 'http://localhost:5173' }
Write-Host 'To stop: close both windows, or run scripts\stop_app.ps1' -ForegroundColor Gray
