#!/usr/bin/env pwsh

Write-Host "🐰 Starting RabbitReels Application..." -ForegroundColor Green

# Check if Docker is running
try {
    docker info | Out-Null
    Write-Host "✅ Docker is running" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker is not running. Please start Docker Desktop first." -ForegroundColor Red
    exit 1
}

# Navigate to project root
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot

# Check if .env file exists
if (-not (Test-Path ".env")) {
    Write-Host "⚠️  .env file not found. Please create one based on .env.example" -ForegroundColor Yellow
}

# Start services using docker-compose
Write-Host "🚀 Starting services with Docker Compose..." -ForegroundColor Blue
docker-compose -f docker-compose-no-publisher.yml up -d

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Services started successfully!" -ForegroundColor Green
    Write-Host ""
    Write-Host "📋 Service URLs:" -ForegroundColor Cyan
    Write-Host "  • Web App: http://localhost:3001" -ForegroundColor White
    Write-Host "  • API: http://localhost:8080" -ForegroundColor White
    Write-Host "  • RabbitMQ Management: http://localhost:15672 (guest/guest)" -ForegroundColor White
    Write-Host "  • Redis: localhost:6379" -ForegroundColor White
    Write-Host ""
    Write-Host "📊 To view logs: docker-compose -f docker-compose-no-publisher.yml logs -f" -ForegroundColor Yellow
    Write-Host "🛑 To stop: docker-compose -f docker-compose-no-publisher.yml down" -ForegroundColor Yellow
} else {
    Write-Host "❌ Failed to start services. Check the logs above." -ForegroundColor Red
    exit 1
}
