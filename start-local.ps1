# Start turniping locally on Windows without Docker.
#
# Assumes one-time setup is already done: the turniping role + database
# exist in the local PostgreSQL service, backend/.venv is populated,
# frontend/node_modules is installed, and backend/.env + frontend/.env.local
# exist (copy from the .example files).
#
# Opens four windows: Redis, the API, the market/news/prediction worker, and Next.js.

$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$redisDir = Join-Path (Split-Path $root -Parent) 'tools\redis\Redis-8.8.0-Windows-x64-msys2'

function Start-Piece($title, $workDir, $exe, $argList) {
    Start-Process -FilePath 'powershell.exe' -WorkingDirectory $workDir -ArgumentList @(
        '-NoExit', '-Command', "`$host.UI.RawUI.WindowTitle='$title'; & '$exe' $argList"
    )
}

# 1. Redis — skip if something already answers on 6379.
$redisUp = try { (New-Object Net.Sockets.TcpClient).Connect('127.0.0.1', 6379); $true } catch { $false }
if ($redisUp) {
    Write-Host 'Redis already listening on 6379 — leaving it alone.'
} else {
    Start-Piece 'redis' $redisDir (Join-Path $redisDir 'redis-server.exe') '--port 6379 --save "" --appendonly no'
    Start-Sleep -Seconds 2
}

$backend = Join-Path $root 'backend'
$py = Join-Path $backend '.venv\Scripts\python.exe'

# 2. API on :8001
Start-Piece 'turniping-api' $backend $py '-m uvicorn app.main:app --reload --port 8001'

# 3. Worker (price polling, news ingest, prediction compute, outcome eval, retention)
Start-Piece 'turniping-worker' $backend $py '-m app.worker.main'

# 4. Frontend on :3002
Start-Piece 'turniping-frontend' (Join-Path $root 'frontend') 'npm.cmd' 'run dev'

Write-Host ''
Write-Host 'Frontend : http://localhost:3002'
Write-Host 'API docs : http://localhost:8001/docs'
