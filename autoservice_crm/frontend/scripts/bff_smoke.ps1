param(
    [string]$BackendUrl = "http://127.0.0.1:8001",
    [string]$FrontendUrl = "http://127.0.0.1:3000"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Step([string]$Message) {
    Write-Host "[bff-smoke] $Message" -ForegroundColor Cyan
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
    throw "Service did not become ready at $Url in $TimeoutSeconds seconds."
}

function Invoke-Json(
    [string]$Method,
    [string]$Url,
    [hashtable]$Headers = @{},
    $Body = $null,
    $Session = $null,
    [switch]$CaptureSession
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
    if ($CaptureSession) {
        $session = $null
        $response = Invoke-WebRequest @params -SessionVariable session
        return [pscustomobject]@{
            Response = $response
            Session = $session
        }
    }
    if ($null -ne $Session) {
        $params["WebSession"] = $Session
    }
    return Invoke-WebRequest @params
}

$backend = $BackendUrl.TrimEnd("/")
$frontend = $FrontendUrl.TrimEnd("/")

Write-Step "Waiting for backend health"
Wait-HttpReady -Url "$backend/health/live" -TimeoutSeconds 60

Write-Step "Waiting for frontend"
Wait-HttpReady -Url $frontend -TimeoutSeconds 60

$suffix = Get-Random -Minimum 10000 -Maximum 99999
$email = "bff+$suffix@example.com"
$password = "BffPass!$suffix"
$tenantSlug = "bff-$suffix"

Write-Step "Registering test tenant via backend"
$registerResponse = Invoke-Json -Method "POST" -Url "$backend/auth/register" -Body @{
    email = $email
    password = $password
    tenant_name = "BFF Tenant $suffix"
    tenant_slug = $tenantSlug
}
$register = $registerResponse.Content | ConvertFrom-Json
if ([string]::IsNullOrWhiteSpace([string]$register.tokens.access_token)) {
    throw "Backend register failed to return access token"
}

Write-Step "Logging in via BFF (cookie session)"
$loginHeaders = @{ Origin = $frontend; Accept = "application/json" }
$loginResponse = Invoke-Json -Method "POST" -Url "$frontend/auth/login" -Headers $loginHeaders -Body @{
    email = $email
    password = $password
    tenantSlug = $tenantSlug
} -CaptureSession
$session = $loginResponse.Session
if ($null -eq $session) {
    throw "Failed to capture session cookies from BFF login"
}

Write-Step "Calling dashboard"
$dash = (Invoke-Json -Method "GET" -Url "$frontend/api/workspace/dashboard" -Session $session).Content | ConvertFrom-Json
if (-not $dash.nowLabel) { throw "Dashboard missing nowLabel" }

Write-Step "Calling today"
$today = (Invoke-Json -Method "GET" -Url "$frontend/api/workspace/today" -Session $session).Content | ConvertFrom-Json
if (-not $today.nowLabel) { throw "Today missing nowLabel" }

Write-Step "Calling cash desk"
$cash = (Invoke-Json -Method "GET" -Url "$frontend/api/workspace/cash-desk" -Session $session).Content | ConvertFrom-Json
if (-not $cash.nowLabel) { throw "Cash desk missing nowLabel" }

Write-Step "Creating client via BFF"
$clientHeaders = @{ Origin = $frontend; Accept = "application/json"; "Idempotency-Key" = ([Guid]::NewGuid().ToString("N")) }
$clientPayload = @{
    name = "BFF Client"
    phone = "79$((Get-Random -Minimum 100000000 -Maximum 999999999))"
    email = "client+$suffix@example.com"
    comment = "bff-smoke"
}
$client = (Invoke-Json -Method "POST" -Url "$frontend/api/workspace/clients" -Headers $clientHeaders -Body $clientPayload -Session $session).Content | ConvertFrom-Json
if (-not $client.id) { throw "Client create failed" }

Write-Step "Creating order via BFF"
$orderHeaders = @{ Origin = $frontend; Accept = "application/json"; "Idempotency-Key" = ([Guid]::NewGuid().ToString("N")) }
$orderPayload = @{
    phone = $clientPayload.phone
    clientName = $clientPayload.name
    description = "BFF order"
    price = 1000
}
$orderResult = (Invoke-Json -Method "POST" -Url "$frontend/api/workspace/orders" -Headers $orderHeaders -Body $orderPayload -Session $session).Content | ConvertFrom-Json
if (-not $orderResult.orderId) { throw "Order create failed" }

Write-Step "Mark order paid via BFF"
$payHeaders = @{ Origin = $frontend; Accept = "application/json" }
$paid = (Invoke-Json -Method "POST" -Url "$frontend/api/workspace/orders/$($orderResult.orderId)/pay" -Headers $payHeaders -Session $session).Content | ConvertFrom-Json
if ($paid.status -ne "completed") { throw "Order pay failed" }

Write-Step "Creating user via BFF"
$userHeaders = @{ Origin = $frontend; Accept = "application/json"; "Idempotency-Key" = ([Guid]::NewGuid().ToString("N")) }
$userPayload = @{
    email = "worker+$suffix@example.com"
    password = "WorkerPass!$suffix"
    role = "employee"
}
$user = (Invoke-Json -Method "POST" -Url "$frontend/api/workspace/users" -Headers $userHeaders -Body $userPayload -Session $session).Content | ConvertFrom-Json
if (-not $user.id) { throw "User create failed" }

Write-Step "Listing orders via BFF"
$orders = (Invoke-Json -Method "GET" -Url "$frontend/api/workspace/orders?limit=5&offset=0" -Session $session).Content | ConvertFrom-Json
if ($orders.total -lt 1) { throw "Orders list expected at least 1" }

Write-Host "" 
Write-Host "BFF smoke test PASSED" -ForegroundColor Green
Write-Host "Backend: $backend"
Write-Host "Frontend: $frontend"
Write-Host "Tenant: $tenantSlug"
Write-Host "Order ID: $($orderResult.orderId)"
