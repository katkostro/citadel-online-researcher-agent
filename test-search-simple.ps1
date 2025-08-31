# Quick test with shorter timeout
$BaseUrl = "https://ca-api-bgtcavgccmsqo.blackpond-b411408c.eastus2.azurecontainerapps.io"

Write-Host "Testing /search endpoint with shorter query..." -ForegroundColor Green

try {
    $Body = @{
        query = "Hello"
    } | ConvertTo-Json

    $Headers = @{
        'Content-Type' = 'application/json'
    }

    Write-Host "Sending simple request..." -ForegroundColor Yellow
    
    $Response = Invoke-RestMethod -Uri "$BaseUrl/search" -Method POST -Body $Body -Headers $Headers -TimeoutSec 120
    
    Write-Host "✅ SUCCESS - Response received:" -ForegroundColor Green
    $Response | ConvertTo-Json -Depth 5 | Write-Host
    
    # Validate response structure
    if ($Response.response -and $Response.response.type -eq "text" -and $Response.response.text.value) {
        Write-Host "✅ Response format is PERFECT!" -ForegroundColor Green
    } else {
        Write-Host "❌ Response format is incorrect!" -ForegroundColor Red
    }
    
} catch {
    Write-Host "❌ Error: $($_.Exception.Message)" -ForegroundColor Red
    if ($_.Exception.Response) {
        Write-Host "   Status Code: $($_.Exception.Response.StatusCode.value__)" -ForegroundColor Red
    }
}
