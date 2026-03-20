param(
    [string]$BaseUrl = "http://127.0.0.1:8000"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Step([string]$Message) {
    Write-Host "[smoke] $Message" -ForegroundColor Cyan
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

function To-Decimal([object]$Value) {
    return [decimal]::Parse([string]$Value, [System.Globalization.CultureInfo]::InvariantCulture)
}

function Assert-True([bool]$Condition, [string]$Message) {
    if (-not $Condition) {
        throw $Message
    }
}

$base = $BaseUrl.TrimEnd("/")

Write-Step "Checking /health/live"
$live = Invoke-Json -Method "GET" -Url "$base/health/live"
Assert-True ($live.status -eq "ok") "health/live failed"

$suffix = Get-Random -Minimum 10000 -Maximum 99999
$email = "smoke+$suffix@example.com"
$password = "SmokePass!$suffix"
$tenantSlug = "smoke-$suffix"

Write-Step "Registering tenant owner"
$register = Invoke-Json -Method "POST" -Url "$base/auth/register" -Body @{
    email = $email
    password = $password
    tenant_name = "Smoke Tenant $suffix"
    tenant_slug = $tenantSlug
}

$token = [string]$register.tokens.access_token
Assert-True (-not [string]::IsNullOrWhiteSpace($token)) "Failed to get access token from /auth/register"
$authHeaders = @{ Authorization = "Bearer $token" }

Write-Step "Checking auth and workspace context"
$me = Invoke-Json -Method "GET" -Url "$base/auth/me" -Headers $authHeaders
Assert-True (-not [string]::IsNullOrWhiteSpace([string]$me.tenant.id)) "/auth/me response does not contain tenant id"
$workspace = Invoke-Json -Method "GET" -Url "$base/workspace/context" -Headers $authHeaders
Assert-True ([string]$workspace.workspace_id -eq [string]$me.tenant.id) "Workspace context mismatch"

Write-Step "Creating client"
$client = Invoke-Json -Method "POST" -Url "$base/clients/" -Headers @{
    Authorization = "Bearer $token"
    "Idempotency-Key" = ([Guid]::NewGuid().ToString("N"))
} -Body @{
    name = "Smoke Client"
    phone = "79$((Get-Random -Minimum 100000000 -Maximum 999999999))"
    email = "client+$suffix@example.com"
    comment = "internal-rollout-smoke"
}
Assert-True (-not [string]::IsNullOrWhiteSpace([string]$client.id)) "Client create failed"

Write-Step "Creating vehicle"
$vehicle = Invoke-Json -Method "POST" -Url "$base/vehicles/" -Headers @{
    Authorization = "Bearer $token"
    "Idempotency-Key" = ([Guid]::NewGuid().ToString("N"))
} -Body @{
    client_id = $client.id
    plate_number = "SMK$suffix"
    make_model = "Smoke Model"
    year = 2020
    vin = "VIN$suffix"
    comment = "smoke-check"
}
Assert-True (-not [string]::IsNullOrWhiteSpace([string]$vehicle.id)) "Vehicle create failed"

Write-Step "Creating employee with manager role"
try {
    $employee = Invoke-Json -Method "POST" -Url "$base/employees/" -Headers @{
        Authorization = "Bearer $token"
        "Idempotency-Key" = ([Guid]::NewGuid().ToString("N"))
    } -Body @{
        email = "manager+$suffix@example.com"
        password = "ManagerPass!$suffix"
        role = "manager"
    }
} catch {
    throw "Employee create failed. If role=manager is rejected, ensure migration 20260313_000004 is applied."
}
Assert-True (-not [string]::IsNullOrWhiteSpace([string]$employee.employee_id)) "Employee create failed"

Write-Step "Creating work-order"
$workOrder = Invoke-Json -Method "POST" -Url "$base/work-orders/" -Headers @{
    Authorization = "Bearer $token"
    "Idempotency-Key" = ([Guid]::NewGuid().ToString("N"))
} -Body @{
    client_id = $client.id
    vehicle_id = $vehicle.id
    assigned_employee_id = $employee.employee_id
    description = "Smoke work-order"
    total_amount = 1000
    status = "new"
}
Assert-True (-not [string]::IsNullOrWhiteSpace([string]$workOrder.id)) "Work-order create failed"

Write-Step "Adding line and payment"
$line = Invoke-Json -Method "POST" -Url "$base/work-orders/$($workOrder.id)/lines" -Headers $authHeaders -Body @{
    line_type = "labor"
    name = "Diagnostics"
    quantity = 1
    unit_price = 1200
    comment = "smoke"
}
Assert-True (-not [string]::IsNullOrWhiteSpace([string]$line.id)) "Order line create failed"

$payment = Invoke-Json -Method "POST" -Url "$base/work-orders/$($workOrder.id)/payments" -Headers $authHeaders -Body @{
    amount = 300
    method = "cash"
    comment = "advance"
}
Assert-True (-not [string]::IsNullOrWhiteSpace([string]$payment.id)) "Payment create failed"

Write-Step "Validating total/paid/remaining semantics"
$orderAfterPayment = Invoke-Json -Method "GET" -Url "$base/work-orders/$($workOrder.id)" -Headers $authHeaders
$totalAmount = To-Decimal $orderAfterPayment.total_amount
$paidAmount = To-Decimal $orderAfterPayment.paid_amount
$remainingAmount = To-Decimal $orderAfterPayment.remaining_amount
$expectedRemaining = $totalAmount - $paidAmount
if ($expectedRemaining -lt 0) {
    $expectedRemaining = 0
}
Assert-True ($remainingAmount -eq $expectedRemaining) "Remaining amount is inconsistent with total and paid"

Write-Step "Changing status and closing work-order"
$null = Invoke-Json -Method "POST" -Url "$base/work-orders/$($workOrder.id)/status" -Headers $authHeaders -Body @{ status = "in_progress" }
$null = Invoke-Json -Method "POST" -Url "$base/work-orders/$($workOrder.id)/status" -Headers $authHeaders -Body @{ status = "completed" }
$closed = Invoke-Json -Method "POST" -Url "$base/work-orders/$($workOrder.id)/close" -Headers $authHeaders
Assert-True ([string]$closed.status -eq "completed") "Work-order close did not result in completed status"

Write-Step "Checking dashboard summary"
$summary = Invoke-Json -Method "GET" -Url "$base/dashboard/summary?recent_limit=5" -Headers $authHeaders
Assert-True ($null -ne $summary.open_work_orders_count) "Dashboard missing open_work_orders_count"
Assert-True ($null -ne $summary.closed_work_orders_count) "Dashboard missing closed_work_orders_count"
Assert-True ($null -ne $summary.revenue_total) "Dashboard missing revenue_total"

Write-Step "Checking workspace settings"
$settings = Invoke-Json -Method "GET" -Url "$base/workspace/settings" -Headers $authHeaders
Assert-True ($null -ne $settings.id) "Workspace settings read failed"
$updatedSettings = Invoke-Json -Method "PATCH" -Url "$base/workspace/settings" -Headers $authHeaders -Body @{
    phone = "70000000000"
}
Assert-True ([string]$updatedSettings.phone -eq "70000000000") "Workspace settings patch failed"

Write-Step "Checking audit list"
$audit = Invoke-Json -Method "GET" -Url "$base/audit/?limit=5&offset=0" -Headers $authHeaders
Assert-True ($null -ne $audit.items) "Audit endpoint did not return items"

Write-Host ""
Write-Host "Smoke test PASSED" -ForegroundColor Green
Write-Host "Base URL: $base"
Write-Host "Tenant: $tenantSlug"
Write-Host "Client ID: $($client.id)"
Write-Host "Vehicle ID: $($vehicle.id)"
Write-Host "Work-order ID: $($workOrder.id)"
