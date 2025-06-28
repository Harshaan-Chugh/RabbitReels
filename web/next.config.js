/** @type {import('next').NextConfig} */
const nextConfig = {
  env: {
    NEXT_PUBLIC_API_BASE: 'https://rabbitreels.us/api',
    NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY: 'pk_live_51RdDyLCcx9hzfp3IoJ2b6QjQuvWaED5K0dTKrGzSStPfggtgLDS75p276FjZTr7NhKMSFrxCKZA9J90D5WzcpJmf00Ok1oFTEN:',
    GOOGLE_AUTH_REDIRECT: 'https://rabbitreels.us/api/auth/callback',
    FRONTEND_URL: 'https://rabbitreels.us'
  },
  images: {
    unoptimized: true
  }
}

module.exports = nextConfig
