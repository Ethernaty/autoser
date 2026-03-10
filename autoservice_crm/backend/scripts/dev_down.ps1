Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Step([string]$Message) {
    Write-Host "[dev_down] $Message" -ForegroundColor Cyan
}

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendDir = Resolve-Path (Join-Path $ScriptDir "..")
Set-Location $BackendDir

$pidPath = Join-Path $BackendDir ".dev-api.pid"
if (Test-Path $pidPath) {
    try {
        $pid = [int](Get-Content $pidPath -Raw).Trim()
        $process = Get-Process -Id $pid -ErrorAction SilentlyContinue
        if ($null -ne $process) {
            Write-Step "Stopping API process PID=$pid"
            Stop-Process -Id $pid -Force
        }
    } catch {
        # ignore invalid PID
    }
    Remove-Item $pidPath -ErrorAction SilentlyContinue
}

Write-Step "Stopping docker dependencies"
docker compose down

Write-Host "Stopped." -ForegroundColor Green
