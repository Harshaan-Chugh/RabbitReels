#!/usr/bin/env pwsh
# Start RabbitReels without YouTube publisher (for local development)

Write-Host "🚀 Starting RabbitReels (Local Mode - No YouTube Publishing)..." -ForegroundColor Green

# Start infrastructure and core services (excluding publisher)
Write-Host "📦 Starting all services except publisher..." -ForegroundColor Yellow
docker compose up -d rabbitmq redis script-generator video-creator api

# Wait for services to be ready
Write-Host "⏳ Waiting for services to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 15

Write-Host "✅ Core services started!" -ForegroundColor Green
Write-Host ""
Write-Host "🌐 Access URLs:" -ForegroundColor White
Write-Host "  Frontend: http://localhost:3001" -ForegroundColor Cyan
Write-Host "  API: http://localhost:8080" -ForegroundColor Cyan
Write-Host "  API Health: http://localhost:8080/health" -ForegroundColor Cyan
Write-Host "  API Docs: http://localhost:8080/docs" -ForegroundColor Cyan
Write-Host "  RabbitMQ Management: http://localhost:15672 (guest/guest)" -ForegroundColor Cyan
Write-Host ""
Write-Host "📝 What's running:" -ForegroundColor White
Write-Host "  ✅ RabbitMQ - Message Queue" -ForegroundColor Green
Write-Host "  ✅ Redis - Job Status Store" -ForegroundColor Green
Write-Host "  ✅ Script Generator - AI Dialog Creation" -ForegroundColor Green  
Write-Host "  ✅ Video Creator - MP4 Rendering" -ForegroundColor Green
Write-Host "  ✅ API Gateway - HTTP Interface" -ForegroundColor Green
Write-Host "  ❌ Publisher - Disabled (No YouTube upload)" -ForegroundColor Red
Write-Host ""
Write-Host "🎬 Now videos will be saved locally for download instead of uploading to YouTube!" -ForegroundColor Cyan
Write-Host ""
Write-Host "🔧 To start the frontend:" -ForegroundColor White
Write-Host "  cd web; npm run dev" -ForegroundColor Gray
Write-Host ""
Write-Host "🎯 To enable YouTube publishing later:" -ForegroundColor White
Write-Host "  docker compose up -d publisher" -ForegroundColor Gray
