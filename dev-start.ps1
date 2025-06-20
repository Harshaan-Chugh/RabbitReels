# PowerShell Development startup script

Write-Host "🚀 Starting RabbitReels Development Environment..." -ForegroundColor Green

# Start infrastructure
Write-Host "📦 Starting Redis & RabbitMQ..." -ForegroundColor Yellow
docker compose up -d rabbitmq redis

# Wait for services to be ready
Write-Host "⏳ Waiting for services to be ready..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

Write-Host "✅ Development environment infrastructure started!" -ForegroundColor Green
Write-Host "🌐 Frontend: http://localhost:3001" -ForegroundColor Cyan
Write-Host "🔧 API: http://localhost:8080" -ForegroundColor Cyan
Write-Host "🐰 RabbitMQ Management: http://localhost:15672" -ForegroundColor Cyan
Write-Host "📊 Redis: localhost:6379" -ForegroundColor Cyan
Write-Host ""
Write-Host "To start the full stack:" -ForegroundColor White
Write-Host "1. Run 'cd api; uvicorn main:app --reload' in one terminal" -ForegroundColor Gray
Write-Host "2. Run 'cd web; npm run dev' in another terminal" -ForegroundColor Gray
Write-Host ""
Write-Host "Or run 'docker compose up web api' to start everything" -ForegroundColor White
