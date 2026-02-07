import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  // Allow external images
  images: {
    remotePatterns: [
      { protocol: 'https', hostname: 'neptun.in.ua' },
      { protocol: 'https', hostname: 'tiles.openfreemap.org' },
    ],
  },

  // Headers for security and caching
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          { key: 'X-Frame-Options', value: 'DENY' },
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          { key: 'Referrer-Policy', value: 'origin-when-cross-origin' },
        ],
      },
      {
        // Cache static SVG maps
        source: '/:file(ukraine_*.svg)',
        headers: [
          { key: 'Cache-Control', value: 'public, max-age=86400, stale-while-revalidate=604800' },
        ],
      },
      {
        // Cache icon assets
        source: '/:file(icon_*)',
        headers: [
          { key: 'Cache-Control', value: 'public, max-age=86400' },
        ],
      },
    ];
  },

  // Rewrites for backward compatibility with Flask URLs
  async rewrites() {
    return [
      // Legacy alarm routes
      { source: '/api/alarms', destination: '/api/alarms/all' },
      { source: '/api/alarms/full', destination: '/api/alarms/all' },
      // Legacy data route
      { source: '/data', destination: '/api/data' },
      // Legacy health route
      { source: '/health', destination: '/api/health' },
      // Legacy presence route
      { source: '/presence', destination: '/api/presence' },
      // Static files compatibility (old /static/ paths)
      { source: '/static/:path*', destination: '/:path*' },
    ];
  },

  // Redirects
  async redirects() {
    return [
      // Telegram channel aliases
      { source: '/community', destination: 'https://t.me/+aBR79kExNQM1ZjZi', permanent: false },
      { source: '/telegram', destination: 'https://t.me/+aBR79kExNQM1ZjZi', permanent: false },
      { source: '/join', destination: 'https://t.me/+aBR79kExNQM1ZjZi', permanent: false },
      { source: '/channel', destination: 'https://t.me/+aBR79kExNQM1ZjZi', permanent: false },
      { source: '/group', destination: 'https://t.me/+aBR79kExNQM1ZjZi', permanent: false },
      { source: '/chat', destination: 'https://t.me/+aBR79kExNQM1ZjZi', permanent: false },
      // SSE disabled - return info about polling
      { source: '/stream', destination: '/api/data', permanent: false },
      { source: '/api/chat/stream', destination: '/api/chat/messages', permanent: false },
      // SEO landing pages from sitemap — redirect to main map
      { source: '/shahed-map', destination: '/', permanent: true },
      { source: '/radar-shahediv', destination: '/', permanent: true },
      { source: '/karta-shahediv', destination: '/', permanent: true },
      { source: '/blackouts', destination: '/', permanent: true },
      { source: '/map', destination: '/', permanent: true },
      // Flask shahed route aliases
      { source: '/shahed', destination: '/', permanent: true },
      { source: '/drones', destination: '/', permanent: true },
      { source: '/radar-shahed', destination: '/', permanent: true },
      { source: '/shahed-radar', destination: '/', permanent: true },
      // Legacy Flask HTML pages
      { source: '/map_only.html', destination: '/', permanent: true },
      { source: '/region.html', destination: '/region/kyiv', permanent: true },
      { source: '/privacy.html', destination: '/privacy', permanent: true },
    ];
  },

  // Standalone output for Docker/Render deployment
  output: 'standalone',

  // Experimental features
  experimental: {
    serverActions: {
      bodySizeLimit: '2mb',
    },
  },

};

export default nextConfig;
