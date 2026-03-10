param(
    [string]$ApiHost = "127.0.0.1",
    [int]$ApiPort = 8000,
    [switch]$SkipPipInstall
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Step([string]$Message) {
    Write-Host "[dev_up] $Message" -ForegroundColor Cyan
}

function New-RandomSecret([int]$Length = 48) {
    $chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()-_=+[]{}"
    $result = New-Object System.Text.StringBuilder
    1..$Length | ForEach-Object {
        $index = Get-Random -Minimum 0 -Maximum $chars.Length
        [void]$result.Append($chars[$index])
    }
    return $result.ToString()
}

function Load-EnvFile([string]$Path) {
    $map = @{}
    foreach ($line in Get-Content $Path) {
        $trimmed = $line.Trim()
        if ([string]::IsNullOrWhiteSpace($trimmed) -or $trimmed.StartsWith("#")) {
            continue
        }
        $pair = $trimmed -split "=", 2
        if ($pair.Count -eq 2) {
            $map[$pair[0].Trim()] = $pair[1].Trim()
        }
    }
    return $map
}

function Save-EnvFile([string]$Path, [hashtable]$Map) {
    $orderedKeys = [System.Collections.Generic.List[string]]::new()
    foreach ($line in Get-Content $Path) {
        $trimmed = $line.Trim()
        if ([string]::IsNullOrWhiteSpace($trimmed) -or $trimmed.StartsWith("#")) {
            continue
        }
        $pair = $trimmed -split "=", 2
        if ($pair.Count -eq 2 -and -not $orderedKeys.Contains($pair[0].Trim())) {
            $orderedKeys.Add($pair[0].Trim())
        }
    }
    foreach ($key in $Map.Keys) {
        if (-not $orderedKeys.Contains([string]$key)) {
            $orderedKeys.Add([string]$key)
        }
    }
    $lines = New-Object System.Collections.Generic.List[string]
    foreach ($key in $orderedKeys) {
        $lines.Add("$key=$($Map[$key])")
    }
    Set-Content -Path $Path -Value $lines -Encoding UTF8
}

function Wait-HttpReady([string]$Url, [int]$TimeoutSeconds = 60) {
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-WebRequest -Uri $Url -Method Get -TimeoutSec 5 -UseBasicParsing
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
                return
            }
        } catch {
            Start-Sleep -Milliseconds 500
            continue
        }
    }
    throw "API did not become ready at $Url in $TimeoutSeconds seconds."
}

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendDir = Resolve-Path (Join-Path $ScriptDir "..")
Set-Location $BackendDir

Write-Step "Checking Docker availability"
docker version | Out-Null

Write-Step "Starting PostgreSQL and Redis via docker compose"
docker compose up -d postgres redis | Out-Null

$envPath = Join-Path $BackendDir ".env"
$envExamplePath = Join-Path $BackendDir ".env.example"

if (-not (Test-Path $envPath)) {
    Write-Step "Creating .env from .env.example"
    Copy-Item $envExamplePath $envPath
}

$envMap = Load-EnvFile $envPath

$envMap["APP_ENV"] = "development"
$envMap["APP_DEBUG"] = "false"
$envMap["DATABASE_URL"] = "postgresql+psycopg://postgres:postgres@localhost:5432/autoservice_saas"
$envMap["REDIS_URL"] = "redis://localhost:6379/0"
$envMap["INTERNAL_SERVICE_AUTH_HEADER"] = "X-Internal-Service-Auth"

if (-not $envMap.ContainsKey("JWT_SECRET_KEY") -or $envMap["JWT_SECRET_KEY"] -match "^replace_with_") {
    $envMap["JWT_SECRET_KEY"] = New-RandomSecret 64
}
if (-not $envMap.ContainsKey("INTERNAL_SERVICE_AUTH_KEY") -or $envMap["INTERNAL_SERVICE_AUTH_KEY"] -match "^replace_with_") {
    $envMap["INTERNAL_SERVICE_AUTH_KEY"] = New-RandomSecret 64
}
if (-not $envMap.ContainsKey("API_KEY_SECRET_PEPPER") -or $envMap["API_KEY_SECRET_PEPPER"] -match "^replace_with_") {
    $envMap["API_KEY_SECRET_PEPPER"] = New-RandomSecret 64
}

Save-EnvFile $envPath $envMap
Write-Step ".env validated/updated"

$venvDir = Join-Path $BackendDir ".venv"
$pythonExe = Join-Path $venvDir "Scripts\python.exe"
if (-not (Test-Path $pythonExe)) {
    Write-Step "Creating virtual environment"
    py -m venv $venvDir
}

if (-not $SkipPipInstall) {
    Write-Step "Installing backend dependencies"
    & $pythonExe -m pip install --upgrade pip | Out-Null
    & $pythonExe -m pip install -r (Join-Path $BackendDir "requirements.txt")
}

Write-Step "Applying Alembic migrations"
& $pythonExe -m alembic upgrade head

$pidPath = Join-Path $BackendDir ".dev-api.pid"
$oldPid = $null
if (Test-Path $pidPath) {
    try {
        $oldPid = [int](Get-Content $pidPath -Raw).Trim()
        $oldProcess = Get-Process -Id $oldPid -ErrorAction SilentlyContinue
        if ($null -ne $oldProcess) {
            Write-Step "Stopping existing API process PID=$oldPid"
            Stop-Process -Id $oldPid -Force
            Start-Sleep -Seconds 1
        }
    } catch {
        # ignore malformed PID file
    }
}

Write-Step "Starting FastAPI server in background"
$arguments = @(
    "-m", "uvicorn",
    "app.main:app",
    "--host", $ApiHost,
    "--port", "$ApiPort",
    "--reload"
)
$process = Start-Process -FilePath $pythonExe -ArgumentList $arguments -WorkingDirectory $BackendDir -PassThru
Set-Content -Path $pidPath -Value "$($process.Id)" -Encoding ASCII

$healthUrl = "http://$ApiHost`:$ApiPort/health/live"
Write-Step "Waiting for API readiness at $healthUrl"
Wait-HttpReady -Url $healthUrl -TimeoutSeconds 60

Write-Host ""
Write-Host "Backend is up." -ForegroundColor Green
Write-Host "API: http://$ApiHost`:$ApiPort"
Write-Host "Docs: http://$ApiHost`:$ApiPort/docs"
Write-Host ""
Write-Host "Run smoke test:" -ForegroundColor Yellow
Write-Host "  .\scripts\smoke.ps1 -BaseUrl http://$ApiHost`:$ApiPort"
Write-Host ""
Write-Host "Stop everything:" -ForegroundColor Yellow
Write-Host "  .\scripts\dev_down.ps1"
