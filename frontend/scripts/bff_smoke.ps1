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

function To-Decimal([object]$Value) {
    return [decimal]::Parse([string]$Value, [System.Globalization.CultureInfo]::InvariantCulture)
}

function Assert-True([bool]$Condition, [string]$Message) {
    if (-not $Condition) {
        throw $Message
    }
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
Assert-True (-not [string]::IsNullOrWhiteSpace([string]$register.tokens.access_token)) "Backend register failed to return access token"

Write-Step "Logging in via BFF (cookie session)"
$writeHeaders = @{ Origin = $frontend; Accept = "application/json" }
$loginResponse = Invoke-Json -Method "POST" -Url "$frontend/auth/login" -Headers $writeHeaders -Body @{
    email = $email
    password = $password
    tenantSlug = $tenantSlug
} -CaptureSession
$session = $loginResponse.Session
Assert-True ($null -ne $session) "Failed to capture session cookies from BFF login"

Write-Step "Checking session and workspace context"
$me = (Invoke-Json -Method "GET" -Url "$frontend/auth/me" -Session $session).Content | ConvertFrom-Json
Assert-True (-not [string]::IsNullOrWhiteSpace([string]$me.workspaceId)) "Session missing workspaceId"
$context = (Invoke-Json -Method "GET" -Url "$frontend/api/workspace/context" -Session $session).Content | ConvertFrom-Json
Assert-True (-not [string]::IsNullOrWhiteSpace([string]$context.workspace_id)) "Workspace context missing workspace_id"

Write-Step "Creating client"
$client = (Invoke-Json -Method "POST" -Url "$frontend/api/workspace/clients" -Headers @{
    Origin = $frontend
    Accept = "application/json"
    "Idempotency-Key" = ([Guid]::NewGuid().ToString("N"))
} -Body @{
    name = "BFF Client"
    phone = "79$((Get-Random -Minimum 100000000 -Maximum 999999999))"
    email = "client+$suffix@example.com"
    comment = "bff-smoke"
} -Session $session).Content | ConvertFrom-Json
Assert-True (-not [string]::IsNullOrWhiteSpace([string]$client.id)) "Client create failed"

Write-Step "Creating vehicle"
$vehicle = (Invoke-Json -Method "POST" -Url "$frontend/api/workspace/vehicles" -Headers @{
    Origin = $frontend
    Accept = "application/json"
    "Idempotency-Key" = ([Guid]::NewGuid().ToString("N"))
} -Body @{
    client_id = $client.id
    plate_number = "BFF$suffix"
    make_model = "BFF Model"
    year = 2021
    vin = "BFFVIN$suffix"
    comment = "bff-smoke"
} -Session $session).Content | ConvertFrom-Json
Assert-True (-not [string]::IsNullOrWhiteSpace([string]$vehicle.id)) "Vehicle create failed"

Write-Step "Creating employee via canonical /employees"
$employee = (Invoke-Json -Method "POST" -Url "$frontend/api/workspace/employees" -Headers @{
    Origin = $frontend
    Accept = "application/json"
    "Idempotency-Key" = ([Guid]::NewGuid().ToString("N"))
} -Body @{
    email = "manager+$suffix@example.com"
    password = "ManagerPass!$suffix"
    role = "manager"
} -Session $session).Content | ConvertFrom-Json
Assert-True (-not [string]::IsNullOrWhiteSpace([string]$employee.employee_id)) "Employee create failed"

Write-Step "Creating work-order via canonical /work-orders"
$workOrder = (Invoke-Json -Method "POST" -Url "$frontend/api/workspace/work-orders" -Headers @{
    Origin = $frontend
    Accept = "application/json"
    "Idempotency-Key" = ([Guid]::NewGuid().ToString("N"))
} -Body @{
    client_id = $client.id
    vehicle_id = $vehicle.id
    description = "BFF work-order"
    total_amount = 1200
    assigned_employee_id = $employee.employee_id
    status = "new"
} -Session $session).Content | ConvertFrom-Json
Assert-True (-not [string]::IsNullOrWhiteSpace([string]$workOrder.id)) "Work-order create failed"

Write-Step "Adding line item"
$line = (Invoke-Json -Method "POST" -Url "$frontend/api/workspace/work-orders/$($workOrder.id)/lines" -Headers $writeHeaders -Body @{
    line_type = "labor"
    name = "Diagnostics"
    quantity = 1
    unit_price = 1200
    comment = "bff-smoke"
} -Session $session).Content | ConvertFrom-Json
Assert-True (-not [string]::IsNullOrWhiteSpace([string]$line.id)) "Line create failed"

Write-Step "Adding payment"
$payment = (Invoke-Json -Method "POST" -Url "$frontend/api/workspace/work-orders/$($workOrder.id)/payments" -Headers $writeHeaders -Body @{
    amount = 300
    method = "cash"
    comment = "advance"
} -Session $session).Content | ConvertFrom-Json
Assert-True (-not [string]::IsNullOrWhiteSpace([string]$payment.id)) "Payment create failed"

Write-Step "Validating total/paid/remaining semantics"
$orderDetail = (Invoke-Json -Method "GET" -Url "$frontend/api/workspace/work-orders/$($workOrder.id)" -Session $session).Content | ConvertFrom-Json
$totalAmount = To-Decimal $orderDetail.total_amount
$paidAmount = To-Decimal $orderDetail.paid_amount
$remainingAmount = To-Decimal $orderDetail.remaining_amount
$expectedRemaining = $totalAmount - $paidAmount
if ($expectedRemaining -lt 0) {
    $expectedRemaining = 0
}
Assert-True ($remainingAmount -eq $expectedRemaining) "remaining_amount is inconsistent"

Write-Step "Changing status and closing"
$null = (Invoke-Json -Method "POST" -Url "$frontend/api/workspace/work-orders/$($workOrder.id)/status" -Headers $writeHeaders -Body @{ status = "in_progress" } -Session $session).Content | ConvertFrom-Json
$null = (Invoke-Json -Method "POST" -Url "$frontend/api/workspace/work-orders/$($workOrder.id)/status" -Headers $writeHeaders -Body @{ status = "completed" } -Session $session).Content | ConvertFrom-Json
$closed = (Invoke-Json -Method "POST" -Url "$frontend/api/workspace/work-orders/$($workOrder.id)/close" -Headers $writeHeaders -Session $session).Content | ConvertFrom-Json
Assert-True ([string]$closed.status -eq "completed") "Work-order close failed"

Write-Step "Checking dashboard summary"
$dashboard = (Invoke-Json -Method "GET" -Url "$frontend/api/workspace/dashboard/summary?recent_limit=5" -Session $session).Content | ConvertFrom-Json
Assert-True ($null -ne $dashboard.open_work_orders_count) "Dashboard missing open_work_orders_count"
Assert-True ($null -ne $dashboard.closed_work_orders_count) "Dashboard missing closed_work_orders_count"
Assert-True ($null -ne $dashboard.revenue_total) "Dashboard missing revenue_total"

Write-Step "Checking workspace settings"
$settings = (Invoke-Json -Method "GET" -Url "$frontend/api/workspace/settings" -Session $session).Content | ConvertFrom-Json
Assert-True ($null -ne $settings.id) "Settings read failed"
$updatedSettings = (Invoke-Json -Method "PATCH" -Url "$frontend/api/workspace/settings" -Headers $writeHeaders -Body @{ phone = "71111111111" } -Session $session).Content | ConvertFrom-Json
Assert-True ([string]$updatedSettings.phone -eq "71111111111") "Settings patch failed"

Write-Step "Checking canonical list endpoints"
$employees = (Invoke-Json -Method "GET" -Url "$frontend/api/workspace/employees?limit=5&offset=0" -Session $session).Content | ConvertFrom-Json
Assert-True ($employees.total -ge 1) "Employees list expected at least 1"
$workOrders = (Invoke-Json -Method "GET" -Url "$frontend/api/workspace/work-orders?limit=5&offset=0" -Session $session).Content | ConvertFrom-Json
Assert-True ($workOrders.total -ge 1) "Work-orders list expected at least 1"

Write-Host ""
Write-Host "BFF smoke test PASSED" -ForegroundColor Green
Write-Host "Backend: $backend"
Write-Host "Frontend: $frontend"
Write-Host "Tenant: $tenantSlug"
Write-Host "Work-order ID: $($workOrder.id)"
