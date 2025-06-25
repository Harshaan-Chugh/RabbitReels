# RabbitReels Deployment Checklist

## Pre-Deployment

- [ ] DigitalOcean droplet created (Ubuntu 22.04 LTS, 2GB+ RAM)
- [ ] SSH access configured
- [ ] Domain name purchased (optional but recommended)
- [ ] All API keys obtained:
  - [ ] OpenAI API key
  - [ ] ElevenLabs API key
  - [ ] Stripe live keys
  - [ ] Google OAuth credentials
- [ ] Repository cloned to server

## Server Setup

- [ ] Non-root user created (`rabbitreels`)
- [ ] Docker installed
- [ ] Docker Compose installed
- [ ] Firewall configured (ports 22, 80, 443)
- [ ] SSL certificates obtained (Let's Encrypt or self-signed)

## Environment Configuration

- [ ] `.env` file created from `env.example`
- [ ] `JWT_SECRET` set (secure random string)
- [ ] `SESSION_SECRET` set (secure random string)
- [ ] `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` configured
- [ ] `STRIPE_SECRET_KEY` and `STRIPE_PUBLISHABLE_KEY` set
- [ ] `STRIPE_WEBHOOK_SECRET` configured
- [ ] `OPENAI_API_KEY` set
- [ ] `ELEVEN_API_KEY` set
- [ ] `FRONTEND_URL` set to your domain
- [ ] `ENVIRONMENT=production` set

## Application Deployment

- [ ] `deploy.sh` script executed
- [ ] All Docker containers built and started
- [ ] Database initialized
- [ ] API health check passes
- [ ] Frontend accessible
- [ ] Google OAuth login working
- [ ] Video generation tested

## Post-Deployment

- [ ] SSL certificate properly configured
- [ ] Domain pointing to server
- [ ] Monitoring set up (logs, resource usage)
- [ ] Backup system configured
- [ ] Security hardening completed:
  - [ ] Fail2ban installed
  - [ ] Automatic security updates enabled
  - [ ] Regular backups scheduled
- [ ] Performance monitoring active

## Testing Checklist

- [ ] API endpoints responding
- [ ] User registration/login working
- [ ] Credit purchase flow functional
- [ ] Video generation pipeline working
- [ ] File downloads working
- [ ] Error handling working properly
- [ ] Rate limiting active

## Security Verification

- [ ] HTTPS redirect working
- [ ] Security headers present
- [ ] Environment variables not exposed
- [ ] Database credentials secure
- [ ] API keys not in logs
- [ ] Firewall blocking unnecessary ports

## Performance Verification

- [ ] Video generation completing in reasonable time
- [ ] Database queries optimized
- [ ] File storage adequate
- [ ] Memory usage within limits
- [ ] CPU usage reasonable under load

## Documentation

- [ ] Deployment guide updated
- [ ] Environment variables documented
- [ ] Troubleshooting procedures documented
- [ ] Contact information for support
- [ ] Monitoring dashboard access

## Emergency Procedures

- [ ] Rollback procedure tested
- [ ] Backup restoration tested
- [ ] Emergency contact list ready
- [ ] Service restart procedures documented
- [ ] Data recovery procedures in place

---

**Deployment Date:** _______________
**Deployed By:** _______________
**Server IP:** _______________
**Domain:** _______________

**Notes:** 