import type { MetadataRoute } from 'next';

const BASE = 'https://neptun.in.ua';

const regionSlugs = [
  'kyiv', 'kyivska', 'kharkivska', 'odeska', 'dnipropetrovska', 'zaporizka',
  'lvivska', 'mykolaivska', 'khersonska', 'poltavska', 'vinnytska', 'cherkaska',
  'zhytomyrska', 'sumska', 'chernihivska', 'rivnenska', 'volynska', 'ternopilska',
  'ivano-frankivska', 'zakarpatska', 'chernivetska', 'khmelnytska', 'kirovohradska',
  'donetska', 'luhanska',
];

const citySlugs = [
  'kharkiv', 'odesa', 'dnipro', 'lviv', 'zaporizhzhia',
  'mykolaiv', 'kyiv-city', 'vinnytsia', 'sumy', 'poltava',
];

const blogSlugs = [
  'shcho-robyty-pid-chas-tryvohy',
  'yak-pratsyuye-karta-shahediv',
  'typy-povitryanykh-zahroz',
  'yak-nalashtuvatу-push-spovishchennya',
  'porivnyannya-kart-tryvoh',
];

export default function sitemap(): MetadataRoute.Sitemap {
  const now = new Date();

  const staticPages: MetadataRoute.Sitemap = [
    // Homepage — highest priority, always fresh
    {
      url: `${BASE}/`,
      lastModified: now,
      changeFrequency: 'always',
      priority: 1.0,
    },
    // Landing / keyword pages
    {
      url: `${BASE}/karta-shahediv`,
      lastModified: now,
      changeFrequency: 'daily',
      priority: 0.9,
    },
    {
      url: `${BASE}/karta-tryvoh`,
      lastModified: now,
      changeFrequency: 'daily',
      priority: 0.9,
    },
    {
      url: `${BASE}/povitryana-tryvoga`,
      lastModified: now,
      changeFrequency: 'daily',
      priority: 0.9,
    },
    {
      url: `${BASE}/tryvoga-zaraz`,
      lastModified: now,
      changeFrequency: 'hourly',
      priority: 0.88,
    },
    {
      url: `${BASE}/radar-shahediv`,
      lastModified: now,
      changeFrequency: 'daily',
      priority: 0.9,
    },
    // Aviation
    {
      url: `${BASE}/aviation`,
      lastModified: now,
      changeFrequency: 'always',
      priority: 0.8,
    },
    // Content pages
    {
      url: `${BASE}/statistics`,
      lastModified: now,
      changeFrequency: 'monthly',
      priority: 0.8,
    },
    {
      url: `${BASE}/blog`,
      lastModified: now,
      changeFrequency: 'weekly',
      priority: 0.8,
    },
    {
      url: `${BASE}/embed`,
      lastModified: now,
      changeFrequency: 'monthly',
      priority: 0.7,
    },
    // Info pages
    {
      url: `${BASE}/about`,
      lastModified: now,
      changeFrequency: 'monthly',
      priority: 0.6,
    },
    {
      url: `${BASE}/faq`,
      lastModified: now,
      changeFrequency: 'monthly',
      priority: 0.7,
    },
    {
      url: `${BASE}/contact`,
      lastModified: now,
      changeFrequency: 'monthly',
      priority: 0.5,
    },
    {
      url: `${BASE}/privacy`,
      lastModified: now,
      changeFrequency: 'yearly',
      priority: 0.3,
    },
    {
      url: `${BASE}/terms`,
      lastModified: now,
      changeFrequency: 'yearly',
      priority: 0.3,
    },
    // English version
    {
      url: `${BASE}/en`,
      lastModified: now,
      changeFrequency: 'always',
      priority: 0.9,
    },
  ];

  // Region pages — hourly freshness (ISR revalidates every 60s)
  const regionPages: MetadataRoute.Sitemap = regionSlugs.map((slug) => ({
    url: `${BASE}/region/${slug}`,
    lastModified: now,
    changeFrequency: 'hourly' as const,
    priority: 0.8,
  }));

  // City pages — hourly freshness (ISR revalidates every 60s)
  const cityPages: MetadataRoute.Sitemap = citySlugs.map((slug) => ({
    url: `${BASE}/city/${slug}`,
    lastModified: now,
    changeFrequency: 'hourly' as const,
    priority: 0.7,
  }));

  // Blog posts
  const blogPages: MetadataRoute.Sitemap = blogSlugs.map((slug) => ({
    url: `${BASE}/blog/${slug}`,
    lastModified: now,
    changeFrequency: 'monthly' as const,
    priority: 0.6,
  }));

  return [...staticPages, ...regionPages, ...cityPages, ...blogPages];
}
