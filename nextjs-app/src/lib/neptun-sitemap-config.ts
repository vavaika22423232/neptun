/**
 * Єдиний список URL для sitemap (`app/sitemap.ts` та `/api/sitemap-xml`).
 * У проді `/sitemap.xml` переписується на API (див. next.config.ts), тому цей модуль — джерело правди.
 */

export const NEPTUN_SITEMAP_BASE = 'https://neptun.in.ua';

export const REGION_SLUGS = [
  'kyiv', 'kyivska', 'kharkivska', 'odeska', 'dnipropetrovska', 'zaporizka',
  'lvivska', 'mykolaivska', 'khersonska', 'poltavska', 'vinnytska', 'cherkaska',
  'zhytomyrska', 'sumska', 'chernihivska', 'rivnenska', 'volynska', 'ternopilska',
  'ivano-frankivska', 'zakarpatska', 'chernivetska', 'khmelnytska', 'kirovohradska',
  'donetska', 'luhanska',
] as const;

export const CITY_SLUGS = [
  'kharkiv', 'odesa', 'dnipro', 'lviv', 'zaporizhzhia',
  'mykolaiv', 'kyiv-city', 'vinnytsia', 'sumy', 'poltava',
] as const;

export const BLOG_SLUGS = [
  'jak-chytaty-kartu-neptun',
  'dzherela-danykh-neptun-tochnist',
  'ukryttya-pid-chas-tryvohy-marshrut',
  'balistychna-zahroza-dii-za-kilka-khvylun',
  'shcho-robyty-pid-chas-tryvohy',
  'yak-pratsyuye-karta-shahediv',
  'typy-povitryanykh-zahroz',
  'yak-nalashtuvatу-push-spovishchennya',
  'porivnyannya-kart-tryvoh',
] as const;

export type ChangeFreq = 'always' | 'hourly' | 'daily' | 'weekly' | 'monthly' | 'yearly';

export interface NeptunSitemapRow {
  loc: string;
  changeFrequency: ChangeFreq;
  priority: number;
}

function loc(path: string): string {
  if (path === '/') return `${NEPTUN_SITEMAP_BASE}/`;
  return `${NEPTUN_SITEMAP_BASE}${path.startsWith('/') ? path : `/${path}`}`;
}

/** Усі рядки sitemap у стабільному порядку (головна першою). */
export function getNeptunSitemapRows(): NeptunSitemapRow[] {
  const staticRows: NeptunSitemapRow[] = [
    { loc: loc('/'), changeFrequency: 'always', priority: 1.0 },
    { loc: loc('/karta-shahediv'), changeFrequency: 'daily', priority: 0.9 },
    { loc: loc('/karta-tryvoh'), changeFrequency: 'daily', priority: 0.9 },
    { loc: loc('/povitryana-tryvoga'), changeFrequency: 'daily', priority: 0.9 },
    { loc: loc('/tryvoga-zaraz'), changeFrequency: 'hourly', priority: 0.88 },
    { loc: loc('/radar-shahediv'), changeFrequency: 'daily', priority: 0.9 },
    { loc: loc('/aviation'), changeFrequency: 'always', priority: 0.8 },
    { loc: loc('/statistics'), changeFrequency: 'monthly', priority: 0.8 },
    { loc: loc('/blog'), changeFrequency: 'weekly', priority: 0.8 },
    { loc: loc('/embed'), changeFrequency: 'monthly', priority: 0.7 },
    { loc: loc('/about'), changeFrequency: 'monthly', priority: 0.6 },
    { loc: loc('/faq'), changeFrequency: 'monthly', priority: 0.7 },
    { loc: loc('/pro-kartu-dzherela'), changeFrequency: 'monthly', priority: 0.78 },
    { loc: loc('/contact'), changeFrequency: 'monthly', priority: 0.5 },
    { loc: loc('/privacy'), changeFrequency: 'yearly', priority: 0.3 },
    { loc: loc('/terms'), changeFrequency: 'yearly', priority: 0.3 },
    { loc: loc('/en'), changeFrequency: 'always', priority: 0.9 },
  ];

  const regionRows: NeptunSitemapRow[] = REGION_SLUGS.map((slug) => ({
    loc: loc(`/region/${slug}`),
    changeFrequency: 'hourly' as const,
    priority: 0.8,
  }));

  const cityRows: NeptunSitemapRow[] = CITY_SLUGS.map((slug) => ({
    loc: loc(`/city/${slug}`),
    changeFrequency: 'hourly' as const,
    priority: 0.7,
  }));

  const blogRows: NeptunSitemapRow[] = BLOG_SLUGS.map((slug) => ({
    loc: loc(`/blog/${slug}`),
    changeFrequency: 'monthly' as const,
    priority: 0.6,
  }));

  return [...staticRows, ...regionRows, ...cityRows, ...blogRows];
}

function escapeXml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

/** XML для відповіді GET /api/sitemap-xml */
export function buildNeptunSitemapXml(lastModDate?: string): string {
  const lastmod = lastModDate ?? new Date().toISOString().slice(0, 10);
  const rows = getNeptunSitemapRows();
  const body = rows
    .map(
      (r) => `  <url>
    <loc>${escapeXml(r.loc)}</loc>
    <lastmod>${lastmod}</lastmod>
    <changefreq>${r.changeFrequency}</changefreq>
    <priority>${r.priority}</priority>
  </url>`,
    )
    .join('\n');

  return `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${body}
</urlset>
`;
}
