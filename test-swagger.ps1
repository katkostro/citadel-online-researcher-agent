# Test Swagger Documentation

# PowerShell script to test the Swagger documentation after deployment

# Get the service URL from azd
$serviceUrl = azd show | Select-String "Endpoints:" -A 10 | Select-String "agent-api" | ForEach-Object { ($_ -split ": ")[1].Trim() }

if (-not $serviceUrl) {
    Write-Host "❌ Could not find service URL. Make sure the service is deployed." -ForegroundColor Red
    exit 1
}

Write-Host "🌐 Service URL: $serviceUrl" -ForegroundColor Green
Write-Host ""

# Test endpoints
$endpoints = @(
    @{ name = "Service Info"; url = "$serviceUrl/" }
    @{ name = "Swagger UI"; url = "$serviceUrl/docs" }
    @{ name = "ReDoc"; url = "$serviceUrl/redoc" }
    @{ name = "OpenAPI Spec"; url = "$serviceUrl/openapi.json" }
    @{ name = "Health Check"; url = "$serviceUrl/health" }
    @{ name = "Agent Info"; url = "$serviceUrl/agent" }
)

Write-Host "📋 Available Endpoints:" -ForegroundColor Cyan
Write-Host "======================" -ForegroundColor Cyan

foreach ($endpoint in $endpoints) {
    Write-Host "📌 $($endpoint.name): $($endpoint.url)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "🔍 Testing API Accessibility..." -ForegroundColor Cyan

# Test basic connectivity
try {
    $response = Invoke-WebRequest -Uri "$serviceUrl/health" -Method GET -UseBasicParsing
    Write-Host "✅ Health check successful (Status: $($response.StatusCode))" -ForegroundColor Green
} catch {
    Write-Host "❌ Health check failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test OpenAPI spec
try {
    $response = Invoke-WebRequest -Uri "$serviceUrl/openapi.json" -Method GET -UseBasicParsing
    $spec = $response.Content | ConvertFrom-Json
    Write-Host "✅ OpenAPI spec accessible (Title: $($spec.info.title), Version: $($spec.info.version))" -ForegroundColor Green
    Write-Host "📊 Endpoints documented: $($spec.paths.PSObject.Properties.Count)" -ForegroundColor Blue
} catch {
    Write-Host "❌ OpenAPI spec failed: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "🎯 Next Steps:" -ForegroundColor Magenta
Write-Host "===============" -ForegroundColor Magenta
Write-Host "1. Open Swagger UI: $serviceUrl/docs" -ForegroundColor White
Write-Host "2. Test endpoints interactively" -ForegroundColor White
Write-Host "3. Copy OpenAPI spec for integration: $serviceUrl/openapi.json" -ForegroundColor White

Write-Host ""
Write-Host "💡 Swagger UI Features:" -ForegroundColor Cyan
Write-Host "- Interactive API testing" -ForegroundColor White
Write-Host "- Request/response examples" -ForegroundColor White
Write-Host "- Schema visualization" -ForegroundColor White  
Write-Host "- Authentication testing" -ForegroundColor White
Write-Host "- Export/import capabilities" -ForegroundColor White
