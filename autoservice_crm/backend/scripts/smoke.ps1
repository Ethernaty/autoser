param(
    [string]$BaseUrl = "http://127.0.0.1:8000",
    [switch]$SkipSecurity
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Step([string]$Message) {
    Write-Host "[smoke] $Message" -ForegroundColor Cyan
}

function Read-EnvValue([string]$EnvPath, [string]$Key) {
    if (-not (Test-Path $EnvPath)) {
        return $null
    }
    foreach ($line in Get-Content $EnvPath) {
        $trimmed = $line.Trim()
        if ([string]::IsNullOrWhiteSpace($trimmed) -or $trimmed.StartsWith("#")) {
            continue
        }
        $pair = $trimmed -split "=", 2
        if ($pair.Count -eq 2 -and $pair[0].Trim() -eq $Key) {
            return $pair[1].Trim()
        }
    }
    return $null
}

function Invoke-Json(
    [string]$Method,
    [string]$Url,
    [hashtable]$Headers = @{},
    $Body = $null
) {
    $params = @{
        Method = $Method
        Uri = $Url
        Headers = $Headers
        TimeoutSec = 30
    }
    if ($null -ne $Body) {
        $params["ContentType"] = "application/json"
        $params["Body"] = ($Body | ConvertTo-Json -Depth 20 -Compress)
    }
    return Invoke-RestMethod @params
}

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendDir = Resolve-Path (Join-Path $ScriptDir "..")
$envPath = Join-Path $BackendDir ".env"
$base = $BaseUrl.TrimEnd("/")

Write-Step "Checking /health/live"
$live = Invoke-Json -Method "GET" -Url "$base/health/live"
if ($live.status -ne "ok") {
    throw "health/live failed"
}

$suffix = Get-Random -Minimum 10000 -Maximum 99999
$email = "smoke+$suffix@example.com"
$password = "SmokePass!$suffix"
$tenantSlug = "smoke-$suffix"

Write-Step "Registering test tenant and owner"
$register = Invoke-Json -Method "POST" -Url "$base/auth/register" -Body @{
    email = $email
    password = $password
    tenant_name = "Smoke Tenant $suffix"
    tenant_slug = $tenantSlug
}

$token = $register.tokens.access_token
if ([string]::IsNullOrWhiteSpace($token)) {
    throw "Failed to get access token from /auth/register"
}
$authHeaders = @{ Authorization = "Bearer $token" }

Write-Step "Calling /auth/me"
$me = Invoke-Json -Method "GET" -Url "$base/auth/me" -Headers $authHeaders
if ([string]::IsNullOrWhiteSpace([string]$me.tenant.id)) {
    throw "/auth/me response does not contain tenant id"
}

$phone = "79$((Get-Random -Minimum 100000000 -Maximum 999999999))"
$idem = [Guid]::NewGuid().ToString("N")
$clientPayload = @{
    name = "Smoke Client"
    phone = $phone
    email = "client+$suffix@example.com"
    comment = "smoke-check"
}

Write-Step "Creating client with idempotency key"
$headersCreate = @{
    Authorization = "Bearer $token"
    "Idempotency-Key" = $idem
}
$client1 = Invoke-Json -Method "POST" -Url "$base/clients/" -Headers $headersCreate -Body $clientPayload
$client2 = Invoke-Json -Method "POST" -Url "$base/clients/" -Headers $headersCreate -Body $clientPayload

if ([string]$client1.id -ne [string]$client2.id) {
    throw "Idempotency check failed: first id '$($client1.id)' second id '$($client2.id)'"
}

Write-Step "Listing clients"
$list = Invoke-Json -Method "GET" -Url "$base/clients/?limit=5&offset=0" -Headers $authHeaders
if ($list.total -lt 1) {
    throw "Expected at least one client in /clients list"
}

if (-not $SkipSecurity) {
    $internalHeader = Read-EnvValue -EnvPath $envPath -Key "INTERNAL_SERVICE_AUTH_HEADER"
    $internalKey = Read-EnvValue -EnvPath $envPath -Key "INTERNAL_SERVICE_AUTH_KEY"

    if ([string]::IsNullOrWhiteSpace($internalHeader) -or [string]::IsNullOrWhiteSpace($internalKey)) {
        throw "INTERNAL_SERVICE_AUTH_HEADER / INTERNAL_SERVICE_AUTH_KEY missing in .env"
    }

    Write-Step "Calling /internal/security-report"
    $securityHeaders = @{ $internalHeader = $internalKey }
    $security = Invoke-Json -Method "GET" -Url "$base/internal/security-report?refresh=false" -Headers $securityHeaders
    if ($null -eq $security.RISK_SCORE) {
        throw "Security report does not contain RISK_SCORE"
    }
}

Write-Host ""
Write-Host "Smoke test PASSED" -ForegroundColor Green
Write-Host "Base URL: $base"
Write-Host "Tenant: $tenantSlug"
Write-Host "Client ID: $($client1.id)"
