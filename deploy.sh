#!/bin/bash

# RabbitReels Production Deployment Script
# For DigitalOcean Droplet: 64.23.135.94

set -e

echo "🚀 Starting RabbitReels Production Deployment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if we're on the production server
if [ "$(hostname)" != "rabbitreels-production" ]; then
    print_warning "This script is designed for the production server (rabbitreels-production)"
    print_warning "Current hostname: $(hostname)"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Create production environment file
print_status "Creating production environment file..."

cat > .env.production << 'EOF'
# RabbitReels Production Environment Configuration
# For DigitalOcean Droplet: 64.23.135.94

# Environment
ENVIRONMENT=production

# Database Configuration
DATABASE_URL=postgresql://rabbitreels:your_secure_postgres_password@postgres:5432/rabbitreels

# Redis Configuration
REDIS_URL=redis://redis:6379/0
REDIS_PASSWORD=your_secure_redis_password

# RabbitMQ Configuration
RABBIT_URL=amqp://guest:guest@rabbitmq:5672/
RABBITMQ_USER=guest
RABBITMQ_PASSWORD=guest

# API Configuration
API_HOST=0.0.0.0
API_PORT=8080
API_RELOAD=false

# Frontend Configuration (Update with your domain when you have one)
FRONTEND_URL=http://64.23.135.94

# Security (REQUIRED - Generate secure random strings)
JWT_SECRET=your-super-secure-jwt-secret-key-here-minimum-32-chars
SESSION_SECRET=your-super-secure-session-secret-key-here-minimum-32-chars

# Google OAuth (REQUIRED)
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_AUTH_REDIRECT=http://64.23.135.94/auth/callback

# Stripe Configuration (REQUIRED for billing)
STRIPE_SECRET_KEY=sk_live_your_stripe_secret_key
STRIPE_PUBLISHABLE_KEY=pk_live_your_stripe_publishable_key
STRIPE_WEBHOOK_SECRET=whsec_your_stripe_webhook_secret

# OpenAI Configuration (REQUIRED for script generation)
OPENAI_API_KEY=sk-your-openai-api-key

# ElevenLabs Configuration (REQUIRED for voice generation)
ELEVEN_API_KEY=your-elevenlabs-api-key
PETER_VOICE_ID=tP8wEHVL4B2h4NuNcRtl
STEWIE_VOICE_ID=u58sF2rOukCb342nzwpN
RICK_VOICE_ID=your-rick-voice-id
MORTY_VOICE_ID=your-morty-voice-id

# Video Processing
VIDEO_OUT_DIR=./data/videos
ENABLE_PUBLISHER=false

# YouTube Publishing (Optional)
YOUTUBE_CLIENT_SECRETS=path/to/credentials.json
YOUTUBE_TOKEN=path/to/youtube-token.json

# PostgreSQL (for docker-compose)
POSTGRES_DB=rabbitreels
POSTGRES_USER=rabbitreels
POSTGRES_PASSWORD=your_secure_postgres_password

# Frontend API Base URL
NEXT_PUBLIC_API_BASE=http://64.23.135.94/api
EOF

print_status "Production environment file created: .env.production"
print_warning "⚠️  IMPORTANT: You need to edit .env.production with your actual API keys and secrets!"

# Create SSL directory for nginx
print_status "Creating SSL directory..."
mkdir -p ssl

# Set proper permissions
print_status "Setting file permissions..."
chmod 600 .env.production
chmod +x deploy.sh

# Open firewall ports
print_status "Opening firewall ports..."
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw allow 8080/tcp  # API (if needed externally)

# Enable firewall
sudo ufw --force enable

print_status "Firewall configured and enabled"

# Build and start services
print_status "Building and starting services..."
docker-compose -f docker-compose.prod.yml --env-file .env.production up -d --build

# Wait for services to be healthy
print_status "Waiting for services to be healthy..."
sleep 30

# Check service status
print_status "Checking service status..."
docker-compose -f docker-compose.prod.yml ps

# Test API health
print_status "Testing API health..."
sleep 10
if curl -f http://localhost:8080/health > /dev/null 2>&1; then
    print_status "✅ API is healthy!"
else
    print_error "❌ API health check failed"
    print_status "Checking API logs..."
    docker-compose -f docker-compose.prod.yml logs api
fi

print_status "🎉 Deployment completed!"
print_status "Your services are running on:"
print_status "  - API: http://64.23.135.94:8080"
print_status "  - Nginx: http://64.23.135.94"
print_status ""
print_warning "Next steps:"
print_warning "1. Edit .env.production with your actual API keys"
print_warning "2. Restart services: docker-compose -f docker-compose.prod.yml --env-file .env.production restart"
print_warning "3. Set up your domain and SSL certificates"
print_warning "4. Configure Stripe webhook to point to: http://64.23.135.94/api/webhook/stripe"
print_warning "5. Update Google OAuth redirect URI to: http://64.23.135.94/auth/callback" 