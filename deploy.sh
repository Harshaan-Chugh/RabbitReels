#!/bin/bash

# RabbitReels Production Deployment Script
# This script sets up the application on a DigitalOcean droplet

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

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   print_error "This script should not be run as root"
   exit 1
fi

# Update system
print_status "Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install Docker
print_status "Installing Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
    print_warning "Docker installed. You may need to log out and back in for group changes to take effect."
else
    print_status "Docker already installed"
fi

# Install Docker Compose
print_status "Installing Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
else
    print_status "Docker Compose already installed"
fi

# Create application directory
APP_DIR="/opt/rabbitreels"
print_status "Creating application directory at $APP_DIR..."
sudo mkdir -p $APP_DIR
sudo chown $USER:$USER $APP_DIR

# Copy application files
print_status "Copying application files..."
cp -r . $APP_DIR/
cd $APP_DIR

# Create SSL directory
sudo mkdir -p /etc/nginx/ssl
sudo chown $USER:$USER /etc/nginx/ssl

# Generate self-signed certificate (replace with Let's Encrypt in production)
print_status "Generating SSL certificate..."
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/nginx/ssl/key.pem \
    -out /etc/nginx/ssl/cert.pem \
    -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"

# Set up environment file
if [ ! -f .env ]; then
    print_warning "No .env file found. Please create one based on env.example"
    print_status "Copying env.example to .env..."
    cp env.example .env
    print_error "Please edit .env file with your production values before continuing"
    exit 1
fi

# Create data directories
print_status "Creating data directories..."
mkdir -p data/videos
mkdir -p logs

# Set proper permissions
print_status "Setting file permissions..."
chmod 600 .env
chmod 755 deploy.sh

# Pull latest images
print_status "Pulling Docker images..."
docker-compose -f docker-compose.prod.yml pull

# Start services
print_status "Starting services..."
docker-compose -f docker-compose.prod.yml up -d

# Wait for services to be healthy
print_status "Waiting for services to be healthy..."
sleep 30

# Check service status
print_status "Checking service status..."
docker-compose -f docker-compose.prod.yml ps

# Test API health
print_status "Testing API health..."
if curl -f http://localhost:8080/health > /dev/null 2>&1; then
    print_status "✅ API is healthy"
else
    print_warning "⚠️  API health check failed. Check logs with: docker-compose -f docker-compose.prod.yml logs api"
fi

# Set up firewall
print_status "Configuring firewall..."
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable

# Create systemd service for auto-start
print_status "Creating systemd service..."
sudo tee /etc/systemd/system/rabbitreels.service > /dev/null <<EOF
[Unit]
Description=RabbitReels Application
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$APP_DIR
ExecStart=/usr/local/bin/docker-compose -f docker-compose.prod.yml up -d
ExecStop=/usr/local/bin/docker-compose -f docker-compose.prod.yml down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable rabbitreels.service

print_status "✅ Deployment completed successfully!"
print_status "📝 Next steps:"
print_status "1. Edit .env file with your production values"
print_status "2. Restart services: docker-compose -f docker-compose.prod.yml restart"
print_status "3. Check logs: docker-compose -f docker-compose.prod.yml logs -f"
print_status "4. Set up domain and SSL certificates"
print_status "5. Configure monitoring and backups"

echo ""
print_status "🌐 Application should be available at:"
echo "   - HTTP: http://$(curl -s ifconfig.me)"
echo "   - HTTPS: https://$(curl -s ifconfig.me) (after SSL setup)" 