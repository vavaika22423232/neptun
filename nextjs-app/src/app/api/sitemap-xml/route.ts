import { NextResponse } from 'next/server';
import { readFileSync, existsSync } from 'fs';
import { join } from 'path';

/**
 * Serves the static sitemap.xml file.
 * Used because the dynamic app/sitemap.ts was causing HTTP 500 in standalone mode.
 */
export async function GET() {
  let xml: string;

  const candidates = [
    join(process.cwd(), 'public', 'sitemap.xml'),
    join(process.cwd(), '..', 'public', 'sitemap.xml'),
    join(process.cwd(), '..', '..', 'public', 'sitemap.xml'),
  ];

  for (const p of candidates) {
    if (existsSync(p)) {
      try {
        xml = readFileSync(p, 'utf-8');
        return new NextResponse(xml, {
          status: 200,
          headers: {
            'Content-Type': 'application/xml; charset=utf-8',
            'Cache-Control': 'public, max-age=3600, s-maxage=3600',
          },
        });
      } catch (e) {
        console.error('[sitemap] Read error:', p, e);
      }
    }
  }

  // Fallback: minimal valid sitemap (homepage only)
  xml = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://neptun.in.ua/</loc><changefreq>always</changefreq><priority>1.0</priority></url>
  <url><loc>https://neptun.in.ua/povitryana-tryvoga</loc><changefreq>daily</changefreq><priority>0.9</priority></url>
  <url><loc>https://neptun.in.ua/tryvoga-zaraz</loc><changefreq>always</changefreq><priority>0.9</priority></url>
  <url><loc>https://neptun.in.ua/karta-tryvoh</loc><changefreq>daily</changefreq><priority>0.9</priority></url>
  <url><loc>https://neptun.in.ua/karta-shahediv</loc><changefreq>daily</changefreq><priority>0.9</priority></url>
  <url><loc>https://neptun.in.ua/radar-shahediv</loc><changefreq>daily</changefreq><priority>0.9</priority></url>
</urlset>`;

  return new NextResponse(xml, {
    status: 200,
    headers: {
      'Content-Type': 'application/xml; charset=utf-8',
      'Cache-Control': 'public, max-age=3600',
    },
  });
}
