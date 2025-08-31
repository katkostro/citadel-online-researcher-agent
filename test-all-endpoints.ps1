# Comprehensive endpoint test
$BaseUrl = "https://ca-api-otr2oya6rbv62.salmoncliff-5eb4c005.eastus2.azurecontainerapps.io"

Write-Host "Testing available endpoints..." -ForegroundColor Green

# Test known working endpoints first
Write-Host "`n=== Testing Known Endpoints ===" -ForegroundColor Cyan

$KnownEndpoints = @(
    @{Path = "/"; Method = "GET"; Name = "Home Page"},
    @{Path = "/agent"; Method = "GET"; Name = "Agent Info"},
    @{Path = "/config/azure"; Method = "GET"; Name = "Azure Config"}
)

foreach ($endpoint in $KnownEndpoints) {
    Write-Host "Testing $($endpoint.Name): $BaseUrl$($endpoint.Path)" -ForegroundColor Yellow
    try {
        $response = Invoke-WebRequest -Uri "$BaseUrl$($endpoint.Path)" -Method $endpoint.Method -TimeoutSec 10
        Write-Host "✅ $($endpoint.Name) - Status: $($response.StatusCode)" -ForegroundColor Green
    } catch {
        Write-Host "❌ $($endpoint.Name) - Error: $($_.Exception.Response.StatusCode.value__)" -ForegroundColor Red
    }
}

# Test POST endpoints
Write-Host "`n=== Testing POST Endpoints ===" -ForegroundColor Cyan

$PostEndpoints = @(
    @{Path = "/chat"; Name = "Chat Endpoint"},
    @{Path = "/search"; Name = "Search Endpoint (NEW)"}
)

foreach ($endpoint in $PostEndpoints) {
    Write-Host "Testing $($endpoint.Name): $BaseUrl$($endpoint.Path)" -ForegroundColor Yellow
    try {
        $body = '{"query": "test"}'
        $headers = @{'Content-Type' = 'application/json'}
        $response = Invoke-WebRequest -Uri "$BaseUrl$($endpoint.Path)" -Method POST -Body $body -Headers $headers -TimeoutSec 10
        Write-Host "✅ $($endpoint.Name) - Status: $($response.StatusCode)" -ForegroundColor Green
    } catch {
        if ($_.Exception.Response) {
            $statusCode = $_.Exception.Response.StatusCode.value__
            if ($statusCode -eq 404) {
                Write-Host "❌ $($endpoint.Name) - NOT FOUND (404)" -ForegroundColor Red
            } else {
                Write-Host "🔶 $($endpoint.Name) - Status: $statusCode (may be auth/validation error)" -ForegroundColor Yellow
            }
        } else {
            Write-Host "❌ $($endpoint.Name) - Error: $($_.Exception.Message)" -ForegroundColor Red
        }
    }
}

Write-Host "`n=== Summary ===" -ForegroundColor Green
Write-Host "If the search endpoint shows 404, the route may not be properly registered." -ForegroundColor Yellow
