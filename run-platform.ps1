# Urban Intelligence Platform - Run all services
# Starts: Backend (8000), ML Service (8001), Frontend (3000)
# Run from the project root

$backendLog = "$env:TEMP\uip-backend.log"
$mlLog = "$env:TEMP\uip-ml.log"
$frontendLog = "$env:TEMP\uip-frontend.log"

Write-Host "=== URBAN INTELLIGENCE PLATFORM - RUNNER ===" -ForegroundColor Cyan
Write-Host ""

function Start-Service {
    param($Name, $Command, $LogFile)
    Write-Host "Starting $Name..." -ForegroundColor Yellow
    $process = Start-Process -FilePath "powershell" -ArgumentList "-NoExit", "-Command", $Command -PassThru -WindowStyle Minimized
    Start-Sleep -Seconds 2
    Write-Host "  $Name started (PID: $($process.Id))." -ForegroundColor Green
    return $process
}

$backendCmd = "cd '$PWD\backend'; python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
$mlCmd = "cd '$PWD\ml-service'; python main.py"
$frontendCmd = "cd '$PWD\frontend'; npm run dev"

$backend = Start-Service -Name "Backend API (port 8000)" -Command $backendCmd -LogFile $backendLog
$ml = Start-Service -Name "ML Service (port 8001)" -Command $mlCmd -LogFile $mlLog
$frontend = Start-Service -Name "Frontend (port 3000)" -Command $frontendCmd -LogFile $frontendLog

Write-Host ""
Write-Host "All services launched!" -ForegroundColor Green
Write-Host ""
Write-Host "  Frontend:  http://localhost:3000" -ForegroundColor White
Write-Host "  Backend:   http://localhost:8000" -ForegroundColor White
Write-Host "  API Docs:  http://localhost:8000/docs" -ForegroundColor White
Write-Host "  ML Service: http://localhost:8001/health" -ForegroundColor White
Write-Host ""
Write-Host "To stop services, close the minimized windows." -ForegroundColor Yellow
Write-Host "Press Enter to close this runner window..." -ForegroundColor Gray
Read-Host