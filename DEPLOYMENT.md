# RabbitReels Production Deployment Guide

## DigitalOcean Droplet Deployment (64.23.135.94)

### ✅ Completed Steps
- [x] Created DigitalOcean droplet
- [x] Installed Docker and Docker Compose
- [x] Set up basic server environment

### 🔄 Next Steps

#### 1. Copy Project to Server
```bash
# From your local machine, copy the project to the server
scp -r . rabbitreels@64.23.135.94:~/rabbitreels
```

#### 2. SSH into Server and Navigate to Project
```bash
ssh rabbitreels@64.23.135.94
cd ~/rabbitreels
```

#### 3. Run Deployment Script
```bash
chmod +x deploy.sh
./deploy.sh
```

#### 4. Configure Environment Variables
**IMPORTANT**: Edit `.env.production` with your actual API keys:

```bash
nano .env.production
```

**Required changes:**
- `JWT_SECRET`: Generate a secure random string (32+ chars)
- `SESSION_SECRET`: Generate a secure random string (32+ chars)
- `GOOGLE_CLIENT_ID`: Your Google OAuth client ID
- `GOOGLE_CLIENT_SECRET`: Your Google OAuth client secret
- `STRIPE_SECRET_KEY`: Your Stripe live secret key
- `STRIPE_PUBLISHABLE_KEY`: Your Stripe live publishable key
- `STRIPE_WEBHOOK_SECRET`: Your Stripe webhook secret
- `OPENAI_API_KEY`: Your OpenAI API key
- `ELEVEN_API_KEY`: Your ElevenLabs API key
- `POSTGRES_PASSWORD`: Generate a secure password
- `REDIS_PASSWORD`: Generate a secure password

#### 5. Restart Services with New Environment
```bash
docker-compose -f docker-compose.prod.yml --env-file .env.production down
docker-compose -f docker-compose.prod.yml --env-file .env.production up -d --build
```

#### 6. Configure External Services

**Stripe Webhook:**
- URL: `http://64.23.135.94/api/webhook/stripe`
- Events: `checkout.session.completed`

**Google OAuth:**
- Redirect URI: `http://64.23.135.94/auth/callback`

#### 7. Test the Deployment
```bash
# Check service status
docker-compose -f docker-compose.prod.yml ps

# Test API health
curl http://64.23.135.94:8080/health

# Check logs if needed
docker-compose -f docker-compose.prod.yml logs -f api
```

### 🌐 Frontend Deployment Options

Since the frontend is not included in `docker-compose.prod.yml`, you have several options:

#### Option A: Deploy Frontend to Vercel/Netlify (Recommended)
1. Push your code to GitHub
2. Connect your repository to Vercel/Netlify
3. Set environment variables:
   - `NEXT_PUBLIC_API_BASE=http://64.23.135.94/api`
4. Deploy

#### Option B: Serve Frontend from the Same Server
1. Add frontend service to `docker-compose.prod.yml`
2. Build and serve static files through nginx

#### Option C: Local Development with Remote Backend
- Keep frontend running locally
- Point to remote API: `http://64.23.135.94/api`

### 🔒 Security Considerations

1. **Firewall**: Already configured to allow only necessary ports
2. **SSL**: Set up Let's Encrypt for HTTPS
3. **Domain**: Point your domain to the server IP
4. **Backups**: Set up regular database backups
5. **Monitoring**: Consider setting up monitoring tools

### 📊 Monitoring and Maintenance

```bash
# View service logs
docker-compose -f docker-compose.prod.yml logs -f

# Check resource usage
docker stats

# Update services
git pull
docker-compose -f docker-compose.prod.yml --env-file .env.production up -d --build

# Backup database
docker-compose -f docker-compose.prod.yml exec postgres pg_dump -U rabbitreels rabbitreels > backup.sql
```

### 🚨 Troubleshooting

**Services not starting:**
```bash
docker-compose -f docker-compose.prod.yml logs
```

**API not responding:**
```bash
docker-compose -f docker-compose.prod.yml logs api
curl http://localhost:8080/health
```

**Database connection issues:**
```bash
docker-compose -f docker-compose.prod.yml exec postgres psql -U rabbitreels -d rabbitreels
```

### 📞 Support

If you encounter issues:
1. Check the logs: `docker-compose -f docker-compose.prod.yml logs -f`
2. Verify environment variables are set correctly
3. Ensure all required API keys are valid
4. Check firewall and network connectivity 