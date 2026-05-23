import type { NextConfig } from 'next';
import { resolveUaRasterTileOrigin } from './src/lib/map/ua-raster-fallback';

const uaRasterOrigin = resolveUaRasterTileOrigin();
let uaRasterHostname: string | undefined;
try {
  uaRasterHostname = uaRasterOrigin ? new URL(uaRasterOrigin).hostname : undefined;
} catch {
  uaRasterHostname = undefined;
}

const uaRasterCsp = uaRasterOrigin ? ` ${uaRasterOrigin}` : '';

/** Pages with ?embed=1 (app WebView, Expo web iframe, partner widgets). */
const embedFrameAncestors =
  "frame-ancestors 'self' https://neptun.in.ua http://localhost:* http://127.0.0.1:* https://localhost:* https://127.0.0.1:*";

function buildContentSecurityPolicy(frameAncestors: string): string {
  return [
    "default-src 'self'",
    "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://www.googletagmanager.com https://unpkg.com https://cdn.jsdelivr.net",
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://unpkg.com https://cdn.jsdelivr.net",
    `img-src 'self' data: blob: https://s3.amazonaws.com https://*.google.com https://*.openfreemap.org https://tiles.openfreemap.org https://basemaps.cartocdn.com https://*.basemaps.cartocdn.com${uaRasterCsp} https://server.arcgisonline.com https://*.arcgisonline.com https://*.tile.openstreetmap.org https://mt1.google.com https://mt2.google.com https://mt3.google.com`,
    `connect-src 'self' https://s3.amazonaws.com https://neptun.in.ua wss://neptun.in.ua https://*.google.com https://*.google-analytics.com https://*.googleapis.com https://tiles.openfreemap.org https://*.openfreemap.org https://basemaps.cartocdn.com https://*.basemaps.cartocdn.com${uaRasterCsp} https://server.arcgisonline.com https://*.arcgisonline.com https://*.tile.openstreetmap.org https://mt1.google.com https://mt2.google.com https://mt3.google.com`,
    "font-src 'self' https://fonts.gstatic.com",
    "worker-src 'self' blob:",
    "child-src 'self' blob:",
    frameAncestors,
    "base-uri 'self'",
    "form-action 'self'",
  ].join('; ');
}

const sharedSecurityHeaders = [
  { key: 'X-Content-Type-Options', value: 'nosniff' },
  { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
  {
    key: 'Strict-Transport-Security',
    value: 'max-age=63072000; includeSubDomains; preload',
  },
  {
    key: 'Permissions-Policy',
    value: 'camera=(), microphone=(), geolocation=(self), payment=()',
  },
] as const;

const nextConfig: NextConfig = {
  poweredByHeader: false,

  images: {
    remotePatterns: [
      { protocol: 'https', hostname: 'neptun.in.ua' },
      { protocol: 'https', hostname: 'tiles.openfreemap.org' },
      { protocol: 'https', hostname: '*.basemaps.cartocdn.com' },
      { protocol: 'https', hostname: '*.tile.openstreetmap.org' },
      ...(uaRasterHostname
        ? [{ protocol: 'https' as const, hostname: uaRasterHostname }]
        : []),
    ],
  },

  async headers() {
    return [
      {
        source: '/:path*',
        missing: [{ type: 'query', key: 'embed', value: '1' }],
        headers: [
          { key: 'X-Frame-Options', value: 'DENY' },
          ...sharedSecurityHeaders,
          {
            key: 'Content-Security-Policy',
            value: buildContentSecurityPolicy("frame-ancestors 'none'"),
          },
        ],
      },
      {
        source: '/:path*',
        has: [{ type: 'query', key: 'embed', value: '1' }],
        headers: [
          ...sharedSecurityHeaders,
          {
            key: 'Content-Security-Policy',
            value: buildContentSecurityPolicy(embedFrameAncestors),
          },
        ],
      },
      {
        source: '/vendor/leaflet/:path*',
        headers: [
          { key: 'Cache-Control', value: 'public, max-age=31536000, stale-while-revalidate=86400, immutable' },
        ],
      },
      {
        source: '/:file(ukraine_*.svg)',
        headers: [
          { key: 'Cache-Control', value: 'public, max-age=604800, stale-while-revalidate=604800, immutable' },
        ],
      },
      {
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
      // Forward old Dron Alerts Android App routes to the new Next.js Map with correct themes
      { source: '/export', destination: '/?embed=1&theme=dark' },
      { source: '/export-light', destination: '/?embed=1&theme=light' },
      { source: '/export.html', destination: '/?embed=1&theme=dark' },
      { source: '/map_only', destination: '/?embed=1' },
      // Sitemap: serve static XML via API (dynamic sitemap.ts caused 500 in standalone)
      { source: '/sitemap.xml', destination: '/api/sitemap-xml' },
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
      // SSE disabled - return info about polling
      { source: '/stream', destination: '/api/data', permanent: false },
      // SEO keyword redirects — redirect synonyms to dedicated landing pages
      { source: '/shahed-map', destination: '/karta-shahediv', permanent: true },
      { source: '/map', destination: '/karta-tryvoh', permanent: true },
      { source: '/mapa-tryvoh', destination: '/karta-tryvoh', permanent: true },
      { source: '/karta-povitryanykh-tryvoh', destination: '/povitryana-tryvoga', permanent: true },
      { source: '/karta-trevog', destination: '/karta-tryvoh', permanent: true },
      { source: '/alert-map', destination: '/karta-tryvoh', permanent: true },
      // Flask shahed route aliases — redirect to landing pages
      { source: '/shahed', destination: '/karta-shahediv', permanent: true },
      { source: '/drones', destination: '/karta-shahediv', permanent: true },
      { source: '/radar-shahed', destination: '/radar-shahediv', permanent: true },
      { source: '/shahed-radar', destination: '/radar-shahediv', permanent: true },
      { source: '/blackouts', destination: '/', permanent: true },
      // Legacy Flask HTML pages
      { source: '/map_only.html', destination: '/', permanent: true },
      { source: '/region.html', destination: '/region/kyiv', permanent: true },
      { source: '/privacy.html', destination: '/privacy', permanent: true },
    ];
  },

  // Standalone output for VPS deployment. Keep dev on the default output so
  // Next can manage its `.next/dev` manifests without fighting standalone mode.
  output: process.env.NODE_ENV === 'production' ? 'standalone' : undefined,

  // Packages that should not be bundled — resolved from node_modules at runtime
  serverExternalPackages: ['firebase-admin', 'bcrypt'],

  // Experimental features
  experimental: {
    serverActions: {
      bodySizeLimit: '2mb',
    },
  },

};

export default nextConfig;
