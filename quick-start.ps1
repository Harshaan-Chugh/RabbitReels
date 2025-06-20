#!/usr/bin/env pwsh
# Quick start script for RabbitReels after setup

Write-Host "🚀 Starting RabbitReels Development Environment..." -ForegroundColor Green

# Start infrastructure services
Write-Host "📦 Starting Redis & RabbitMQ..." -ForegroundColor Yellow
docker compose up -d rabbitmq redis

# Wait for services to be ready
Write-Host "⏳ Waiting for services to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

Write-Host "✅ Infrastructure started!" -ForegroundColor Green
Write-Host ""
Write-Host "🌐 Access URLs:" -ForegroundColor White
Write-Host "  Frontend: http://localhost:3001" -ForegroundColor Cyan
Write-Host "  API: http://localhost:8080" -ForegroundColor Cyan
Write-Host "  RabbitMQ Management: http://localhost:15672 (guest/guest)" -ForegroundColor Cyan
Write-Host ""
Write-Host "🔧 To start the services manually:" -ForegroundColor White
Write-Host "  API: .\.venv\Scripts\Activate.ps1; cd api; uvicorn main:app --reload" -ForegroundColor Gray
Write-Host "  Frontend: cd web; npm run dev" -ForegroundColor Gray
Write-Host ""
Write-Host "🐳 Or start everything with Docker:" -ForegroundColor White
Write-Host "  docker compose up -d" -ForegroundColor Gray
Write-Host ""
Write-Host "Press any key to start API and Frontend automatically..."
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

# Start API in background
Write-Host "🔧 Starting API server..." -ForegroundColor Yellow
$apiJob = Start-Job -ScriptBlock {
    Set-Location $args[0]
    & .venv\Scripts\Activate.ps1
    Set-Location api
    uvicorn main:app --reload --host 0.0.0.0 --port 8080
} -ArgumentList (Get-Location).Path

# Start Frontend in background
Write-Host "🌐 Starting Frontend server..." -ForegroundColor Yellow
$frontendJob = Start-Job -ScriptBlock {
    Set-Location $args[0]
    Set-Location web
    npm run dev
} -ArgumentList (Get-Location).Path

Write-Host "✅ Both servers starting..." -ForegroundColor Green
Write-Host "🌐 Frontend will be available at: http://localhost:3001" -ForegroundColor Cyan
Write-Host "🔧 API will be available at: http://localhost:8080" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press Ctrl+C to stop all services..." -ForegroundColor Yellow

# Wait for user interrupt
try {
    while ($true) {
        Start-Sleep -Seconds 1
        
        # Check if jobs are still running
        if ($apiJob.State -eq "Failed") {
            Write-Host "❌ API job failed" -ForegroundColor Red
            Receive-Job $apiJob
            break
        }
        if ($frontendJob.State -eq "Failed") {
            Write-Host "❌ Frontend job failed" -ForegroundColor Red
            Receive-Job $frontendJob
            break
        }
    }
} finally {
    # Cleanup
    Write-Host "`n🛑 Stopping services..." -ForegroundColor Yellow
    Stop-Job $apiJob, $frontendJob -PassThru | Remove-Job -Force
    docker compose down
    Write-Host "✅ All services stopped" -ForegroundColor Green
}
