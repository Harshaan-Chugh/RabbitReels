/** @type {import('next').NextConfig} */
const nextConfig = {
  env: {
    NEXT_PUBLIC_API_BASE: 'http://localhost:8080/api',
    NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY: 'pk_live_51RdDyLCcx9hzfp3IoJ2b6QjQuvWaED5K0dTKrGzSStPfggtgLDS75p276FjZTr7NhKMSFrxCKZA9J90D5WzcpJmf00Ok1oFTEN:',
    GOOGLE_AUTH_REDIRECT: 'http://localhost:8080/api/auth/callback',
    FRONTEND_URL: 'http://localhost:3001'
  },
  images: {
    unoptimized: true
  }
}

module.exports = nextConfig
