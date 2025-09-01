# Test the new /search endpoint
$BaseUrl = "https://ca-api-bgtcavgccmsqo.greencoast-4ed3b0ae.eastus2.azurecontainerapps.io"

Write-Host "Testing /search endpoint..." -ForegroundColor Green

try {
    $Body = @{
        message = "What is the weather in NYC today?"
    } | ConvertTo-Json

    $Headers = @{
        'Content-Type' = 'application/json'
    }

    Write-Host "Sending request to: $BaseUrl/search" -ForegroundColor Yellow
    Write-Host "Request body: $Body" -ForegroundColor Gray
    
    $Response = Invoke-RestMethod -Uri "$BaseUrl/search" -Method POST -Body $Body -Headers $Headers -TimeoutSec 120
    
    Write-Host "✅ SUCCESS - Response received:" -ForegroundColor Green
    $Response | ConvertTo-Json -Depth 5 | Write-Host
    
    # Validate response structure
    if ($Response.response -and $Response.response.type -eq "text" -and $Response.response.text.value) {
        Write-Host "✅ Response format is correct!" -ForegroundColor Green
    } else {
        Write-Host "❌ Response format is incorrect!" -ForegroundColor Red
    }
    
} catch {
    Write-Host "❌ FAILED: $($_.Exception.Message)" -ForegroundColor Red
    if ($_.Exception.Response) {
        Write-Host "   Status Code: $($_.Exception.Response.StatusCode.value__)" -ForegroundColor Red
    }
}
