# RabbitReels Production Deployment Guide

This guide will help you deploy RabbitReels to a DigitalOcean droplet for production use.

## Prerequisites

- A DigitalOcean account
- A domain name (optional but recommended)
- API keys for required services (OpenAI, ElevenLabs, Stripe, Google OAuth)

## Step 1: Create DigitalOcean Droplet

1. **Create a new droplet:**
   - Choose Ubuntu 22.04 LTS
   - Select a plan with at least 2GB RAM and 2 vCPUs
   - Choose a datacenter close to your target users
   - Add your SSH key for secure access

2. **Connect to your droplet:**
   ```bash
   ssh root@your-droplet-ip
   ```

## Step 2: Prepare the Server

1. **Create a non-root user:**
   ```bash
   adduser rabbitreels
   usermod -aG sudo rabbitreels
   su - rabbitreels
   ```

2. **Clone the repository:**
   ```bash
   git clone https://github.com/your-username/RabbitReels.git
   cd RabbitReels
   ```

3. **Run the deployment script:**
   ```bash
   chmod +x deploy.sh
   ./deploy.sh
   ```

## Step 3: Configure Environment Variables

1. **Copy the environment template:**
   ```bash
   cp env.example .env
   ```

2. **Edit the .env file with your production values:**
   ```bash
   nano .env
   ```

   **Required variables to set:**
   - `JWT_SECRET`: Generate a secure random string
   - `SESSION_SECRET`: Generate another secure random string
   - `GOOGLE_CLIENT_ID`: Your Google OAuth client ID
   - `GOOGLE_CLIENT_SECRET`: Your Google OAuth client secret
   - `STRIPE_SECRET_KEY`: Your Stripe live secret key
   - `STRIPE_PUBLISHABLE_KEY`: Your Stripe live publishable key
   - `STRIPE_WEBHOOK_SECRET`: Your Stripe webhook secret
   - `OPENAI_API_KEY`: Your OpenAI API key
   - `ELEVEN_API_KEY`: Your ElevenLabs API key
   - `FRONTEND_URL`: Your domain (e.g., https://yourdomain.com)

3. **Generate secure secrets:**
   ```bash
   # Generate JWT secret
   openssl rand -base64 32
   
   # Generate session secret
   openssl rand -base64 32
   ```

## Step 4: Set Up Domain and SSL (Optional but Recommended)

1. **Point your domain to the droplet:**
   - Add an A record pointing to your droplet's IP address
   - Wait for DNS propagation (can take up to 24 hours)

2. **Install Certbot for Let's Encrypt SSL:**
   ```bash
   sudo apt install certbot python3-certbot-nginx
   ```

3. **Obtain SSL certificate:**
   ```bash
   sudo certbot --nginx -d yourdomain.com
   ```

4. **Update nginx configuration:**
   - Replace the self-signed certificate paths in `nginx.conf`
   - Update the certificate paths to use Let's Encrypt certificates

## Step 5: Start the Application

1. **Start all services:**
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

2. **Check service status:**
   ```bash
   docker-compose -f docker-compose.prod.yml ps
   ```

3. **View logs:**
   ```bash
   docker-compose -f docker-compose.prod.yml logs -f
   ```

## Step 6: Verify Deployment

1. **Test the API:**
   ```bash
   curl https://yourdomain.com/health
   ```

2. **Test the frontend:**
   - Visit `https://yourdomain.com` in your browser
   - Try logging in with Google OAuth
   - Test video generation

## Step 7: Set Up Monitoring and Backups

### Monitoring

1. **Set up log rotation:**
   ```bash
   sudo nano /etc/logrotate.d/rabbitreels
   ```
   ```
   /opt/rabbitreels/logs/*.log {
       daily
       missingok
       rotate 52
       compress
       delaycompress
       notifempty
       create 644 rabbitreels rabbitreels
   }
   ```

2. **Monitor system resources:**
   ```bash
   # Install htop for system monitoring
   sudo apt install htop
   
   # Monitor Docker containers
   docker stats
   ```

### Backups

1. **Set up database backups:**
   ```bash
   # Create backup script
   nano backup.sh
   ```
   ```bash
   #!/bin/bash
   BACKUP_DIR="/opt/rabbitreels/backups"
   DATE=$(date +%Y%m%d_%H%M%S)
   
   mkdir -p $BACKUP_DIR
   
   # Backup PostgreSQL
   docker-compose -f docker-compose.prod.yml exec -T postgres pg_dump -U rabbitreels rabbitreels > $BACKUP_DIR/db_backup_$DATE.sql
   
   # Backup videos
   tar -czf $BACKUP_DIR/videos_backup_$DATE.tar.gz data/videos/
   
   # Keep only last 7 days of backups
   find $BACKUP_DIR -name "*.sql" -mtime +7 -delete
   find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete
   ```

2. **Set up automated backups:**
   ```bash
   chmod +x backup.sh
   crontab -e
   # Add: 0 2 * * * /opt/rabbitreels/backup.sh
   ```

## Step 8: Security Hardening

1. **Configure firewall:**
   ```bash
   sudo ufw status
   sudo ufw allow 22/tcp
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   sudo ufw --force enable
   ```

2. **Set up fail2ban:**
   ```bash
   sudo apt install fail2ban
   sudo systemctl enable fail2ban
   sudo systemctl start fail2ban
   ```

3. **Regular security updates:**
   ```bash
   # Set up automatic security updates
   sudo apt install unattended-upgrades
   sudo dpkg-reconfigure -plow unattended-upgrades
   ```

## Troubleshooting

### Common Issues

1. **Services not starting:**
   ```bash
   # Check logs
   docker-compose -f docker-compose.prod.yml logs api
   
   # Check environment variables
   docker-compose -f docker-compose.prod.yml config
   ```

2. **Database connection issues:**
   ```bash
   # Check PostgreSQL logs
   docker-compose -f docker-compose.prod.yml logs postgres
   
   # Test database connection
   docker-compose -f docker-compose.prod.yml exec postgres psql -U rabbitreels -d rabbitreels
   ```

3. **SSL certificate issues:**
   ```bash
   # Check certificate validity
   openssl x509 -in /etc/nginx/ssl/cert.pem -text -noout
   
   # Test nginx configuration
   sudo nginx -t
   ```

### Performance Optimization

1. **Scale workers:**
   ```bash
   # Scale video creator workers
   docker-compose -f docker-compose.prod.yml up -d --scale video-creator=2
   ```

2. **Monitor resource usage:**
   ```bash
   # Check container resource usage
   docker stats
   
   # Check system resources
   htop
   ```

## Maintenance

### Regular Maintenance Tasks

1. **Update application:**
   ```bash
   git pull origin main
   docker-compose -f docker-compose.prod.yml build
   docker-compose -f docker-compose.prod.yml up -d
   ```

2. **Clean up Docker:**
   ```bash
   docker system prune -f
   docker volume prune -f
   ```

3. **Monitor disk space:**
   ```bash
   df -h
   du -sh /opt/rabbitreels/data/videos/
   ```

### Emergency Procedures

1. **Restart all services:**
   ```bash
   docker-compose -f docker-compose.prod.yml restart
   ```

2. **Rollback to previous version:**
   ```bash
   git checkout <previous-commit>
   docker-compose -f docker-compose.prod.yml up -d
   ```

3. **Emergency shutdown:**
   ```bash
   docker-compose -f docker-compose.prod.yml down
   ```

## Support

If you encounter issues:

1. Check the logs: `docker-compose -f docker-compose.prod.yml logs -f`
2. Verify environment variables are set correctly
3. Check system resources and disk space
4. Review the troubleshooting section above

For additional help, please check the project documentation or create an issue in the repository. 