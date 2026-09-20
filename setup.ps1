# Urban Intelligence Platform - Windows setup and run
# Run this from the project root

Write-Host "=== URBAN INTELLIGENCE PLATFORM ===" -ForegroundColor Cyan

Write-Host ""
Write-Host "[1/3] Installing backend dependencies..." -ForegroundColor Yellow
python -m pip install -r backend\requirements.txt --quiet

Write-Host "[2/3] Installing ML service dependencies..." -ForegroundColor Yellow
python -m pip install -r ml-service\requirements.txt --quiet

Write-Host "[3/3] Installing frontend dependencies..." -ForegroundColor Yellow
if (-Not (Test-Path "frontend\node_modules")) {
    Push-Location frontend
    npm install
    Pop-Location
} else {
    Write-Host "  Frontend dependencies already installed." -ForegroundColor Green
}

Write-Host ""
Write-Host "Setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "Run the platform with:" -ForegroundColor Cyan
Write-Host "  .\run-platform.ps1" -ForegroundColor White