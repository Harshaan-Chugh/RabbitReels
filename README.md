# RabbitReels

RabbitReels is a distributed AI-agent pipeline powered by RabbitMQ that automates the end-to-end creation and publication of YouTube Shorts. It features a script-generator service that produces concise video narratives, a video-creator service that transforms those scripts into MP4 clips using AI-driven rendering tools, and a publisher service that handles seamless uploads to YouTube—ensuring scalable, fault-tolerant content delivery at every step.

## 🔐 Authentication

RabbitReels now includes **Google OAuth 2.0 authentication** to secure the API and prepare for future payment integration:

- **Google Sign-In**: Users authenticate with their Google accounts
- **JWT Tokens**: Secure API access with JSON Web Tokens
- **Protected Endpoints**: Video creation requires authentication
- **User Tracking**: All video jobs are associated with authenticated users

### Quick Start with Authentication

1. **Set up Google OAuth** (see [OAUTH_SETUP.md](./OAUTH_SETUP.md))
2. **Set up Environment Variables** (see [.env.example](./.env.example)) and train your voice models with [speech-files](speech-files)
3. **Start the services**:
   ```bash
   docker run -d -p 6379:6379 redis:7-alpine
   docker run -d -p 5672:5672 rabbitmq:3-management
   cd api && python main.py
   ```
4. **Visit** `http://localhost:8080` and sign in with Google
5. **Create videos** using the authenticated API

## 🏗️ Architecture

The system consists of:

- **FastAPI Web Layer**: HTTP API with Google OAuth authentication
- **Script Generator**: AI-powered script creation
- **Video Creator**: MP4 rendering with character voices
- **Publisher**: YouTube upload automation
- **RabbitMQ**: Message queue for scalable processing
- **Redis**: Job status tracking and user sessions

## 📚 Documentation

- [OAuth Setup Guide](./OAUTH_SETUP.md) - Google authentication configuration
- [API Documentation](./api/README.md) - Endpoint reference
- [Video Creator](./video-creator/README.md) - Video processing pipeline
- [Publisher](./publisher/README.md) - YouTube integration

## 🚀 Next Steps

- [ ] Stripe payment integration
- [ ] Usage limits and billing tiers  
- [ ] Enhanced web frontend
- [ ] Video template customization
- [ ] Advanced analytics dashboard    