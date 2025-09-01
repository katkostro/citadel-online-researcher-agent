# Test script for /chat endpoint

Write-Host "Testing /chat endpoint..." -ForegroundColor Cyan

$endpoint = "" #e.g. chat endpoint "https://ca-api-bgt.greencoast.eastus2.azurecontainerapps.io/chat"
$body = @{
    message = "What is the weather in NYC today?"
} | ConvertTo-Json

Write-Host "Sending request to: $endpoint"
Write-Host "Request body: $body"

try {
    $response = Invoke-RestMethod -Uri $endpoint -Method Post -Body $body -ContentType "application/json"
    Write-Host "✅ SUCCESS - Response received:" -ForegroundColor Green
    Write-Host "Response type: $($response.GetType())" -ForegroundColor Yellow
    
    # Chat endpoint returns a streaming response, so this might not work as expected
    if ($response) {
        Write-Host "Response content: $response" -ForegroundColor White
    }
    
} catch {
    Write-Host "❌ ERROR: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Status Code: $($_.Exception.Response.StatusCode.value__)" -ForegroundColor Red
}
