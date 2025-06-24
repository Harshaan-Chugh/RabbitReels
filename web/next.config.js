/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'export',
  trailingSlash: false,
  skipTrailingSlashRedirect: false,
  distDir: 'out',
  images: {
    unoptimized: true
  },
  assetPrefix: process.env.NODE_ENV === 'production' ? '' : '',
  basePath: '',
  async redirects() {
    return [
      {
        source: '/billing',
        destination: '/billing/',
        permanent: true,
      },
      {
        source: '/generator',
        destination: '/generator/',
        permanent: true,
      },
    ]
  },
}

module.exports = nextConfig
