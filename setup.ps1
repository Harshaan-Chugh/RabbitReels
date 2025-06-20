#!/usr/bin/env pwsh
# Complete setup script for RabbitReels

Write-Host "🚀 Setting up RabbitReels Development Environment..." -ForegroundColor Green

# Check if Docker is running
try {
    docker version | Out-Null
    Write-Host "✅ Docker is running" -ForegroundColor Green
} catch {
    Write-Host "❌ Docker is not running. Please start Docker Desktop first." -ForegroundColor Red
    exit 1
}

# Check if Python is available
try {
    python --version | Out-Null
    Write-Host "✅ Python is available" -ForegroundColor Green
} catch {
    Write-Host "❌ Python is not available. Please install Python first." -ForegroundColor Red
    exit 1
}

# Check if Node.js is available
try {
    node --version | Out-Null
    Write-Host "✅ Node.js is available" -ForegroundColor Green
} catch {
    Write-Host "❌ Node.js is not available. Please install Node.js first." -ForegroundColor Red
    exit 1
}

# Setup Python virtual environment for API
Write-Host "🐍 Setting up Python environment for API..." -ForegroundColor Yellow
if (-Not (Test-Path ".venv")) {
    python -m venv .venv
    Write-Host "Created Python virtual environment" -ForegroundColor Green
}

# Activate virtual environment and install API dependencies
Write-Host "📦 Installing API dependencies..." -ForegroundColor Yellow
& .venv\Scripts\Activate.ps1
pip install -r api\requirements.txt
Write-Host "✅ API dependencies installed" -ForegroundColor Green

# Install frontend dependencies
Write-Host "📦 Installing frontend dependencies..." -ForegroundColor Yellow
Set-Location web
npm install
Set-Location ..
Write-Host "✅ Frontend dependencies installed" -ForegroundColor Green

# Test Docker Compose configuration
Write-Host "🐳 Testing Docker Compose configuration..." -ForegroundColor Yellow
docker compose config > $null
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Docker Compose configuration is valid" -ForegroundColor Green
} else {
    Write-Host "❌ Docker Compose configuration has errors" -ForegroundColor Red
    exit 1
}

Write-Host "`n🎉 Setup completed successfully!" -ForegroundColor Green
Write-Host "`nNext steps:" -ForegroundColor White
Write-Host "1. Start infrastructure: docker compose up -d rabbitmq redis" -ForegroundColor Gray
Write-Host "2. Start API: .\.venv\Scripts\Activate.ps1; cd api; uvicorn main:app --reload" -ForegroundColor Gray
Write-Host "3. Start frontend: cd web; npm run dev" -ForegroundColor Gray
Write-Host "`nOr use the quick start script: .\quick-start.ps1" -ForegroundColor White
