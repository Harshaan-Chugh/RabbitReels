# Google OAuth Setup Guide

## 1. Google Cloud Console Setup

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google+ API:
   - Go to "APIs & Services" > "Library"
   - Search for "Google+ API"
   - Click "Enable"

## 2. Create OAuth 2.0 Credentials

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth 2.0 Client ID"
3. If prompted, configure the OAuth consent screen:
   - Choose "External" user type
   - Fill in the application name: "RabbitReels"
   - Add your email as the developer contact
   - Add scopes: `email`, `profile`, `openid`
   - Add test users (your email address)

4. For the OAuth 2.0 Client ID:
   - Application type: "Web application"
   - Name: "RabbitReels Web Client"
   - Authorized JavaScript origins: `http://localhost:8080`
   - Authorized redirect URIs: `http://localhost:8080/auth/callback`

5. Download the credentials JSON file (usually labeled as `client_secret_<client-id>.json`) or copy the Client ID and Client Secret

## 3. Environment Variables

Create a `.env` file in the project root with:

```env
# Google OAuth Configuration
GOOGLE_CLIENT_ID=your-google-client-id.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_AUTH_REDIRECT=http://localhost:8080/auth/callback

# JWT Configuration
JWT_SECRET=your-super-secret-jwt-signing-key-change-this-in-production
```

## 4. Production Considerations

- Use a secure, random JWT secret (e.g., generated with `openssl rand -hex 32`)
- Update the redirect URI to your production domain
- Configure CORS origins appropriately
- Consider using secure cookies instead of localStorage for JWT storage
- Add rate limiting for authentication endpoints
- Implement proper token refresh mechanisms

## 5. Testing

1. Start Redis: `docker run -d -p 6379:6379 redis:7-alpine`
2. Start RabbitMQ: `docker run -d -p 5672:5672 rabbitmq:3-management`
3. Start the API: `python main.py`
4. Visit: `http://localhost:8080`
5. Click "Sign in with Google"
6. Test the authenticated API endpoints
