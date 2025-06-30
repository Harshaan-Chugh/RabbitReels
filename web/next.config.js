/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',
  env: {
    NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY: process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY || 'pk_test_your_stripe_publishable_key',
    GOOGLE_AUTH_REDIRECT: 'http://localhost:8080/api/auth/callback',
    FRONTEND_URL: 'http://localhost'
  },
  images: {
    unoptimized: true
  }
}

module.exports = nextConfig
