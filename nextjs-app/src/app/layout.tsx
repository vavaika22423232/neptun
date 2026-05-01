import type { Metadata, Viewport } from 'next';
import { Inter } from 'next/font/google';
import { headers } from 'next/headers';
import DeferredGoogleAnalytics from '@/components/DeferredGoogleAnalytics';
import { pathnameAssetHints } from '@/lib/neptun-pathname-assets';
import { CACHE_VERSION } from '@/lib/constants';
import './globals.css';

const inter = Inter({
  subsets: ['latin', 'cyrillic'],
  weight: ['400', '500', '600', '700'],
  display: 'swap',
  variable: '--font-inter',
});

export const metadata: Metadata = {
  title: 'Карта шахедів і тривог України — повітряна тривога онлайн, мапа тривог | NEPTUN',
  description:
    'Карта шахедів і повітряних тривог України онлайн. Мапа тривог у реальному часі: шахеди, ракети, БПЛА, КАБ. Радар шахедів з траєкторіями, тривоги по областях 24/7. Безкоштовний додаток.',
  keywords:
    'карта шахедів, карта шахедов, радар шахедів, карта тривог, мапа тривог, карта повітряних тривог, повітряна тривога, повітряна тривога онлайн, повітряна тривога онлайн карта що летить, карта тривог україни, мапа тривог онлайн, тривога зараз, нептун, нептун карта, NEPTUN',
  authors: [{ name: 'NEPTUN' }],
  robots: 'index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1',
  alternates: {
    canonical: 'https://neptun.in.ua/',
    languages: {
      uk: 'https://neptun.in.ua/',
      en: 'https://neptun.in.ua/?lang=en',
    },
  },
  openGraph: {
    type: 'website',
    url: 'https://neptun.in.ua/',
    title: 'NEPTUN — Карта шахедів і тривог України онлайн',
    description:
      'Карта шахедів та повітряних тривог онлайн: ракети, БПЛА, КАБ. Оновлення швидко. Безкоштовний додаток.',
    images: [
      {
        url: 'https://neptun.in.ua/static/og-image.png',
        width: 1200,
        height: 630,
      },
    ],
    siteName: 'NEPTUN Карта тривог',
    locale: 'uk_UA',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'NEPTUN — Карта шахедів і тривог України онлайн',
    description: 'Карта шахедів та повітряних тривог онлайн: ракети, БПЛА, КАБ. Швидше за alerts.in.ua. Безкоштовно.',
    images: ['https://neptun.in.ua/static/og-image.png'],
  },
  other: {
    'geo.region': 'UA',
    'geo.placename': 'Ukraine',
    language: 'Ukrainian',
    googlebot: 'index, follow',
    'format-detection': 'telephone=no',
    'apple-mobile-web-app-capable': 'yes',
    'apple-mobile-web-app-status-bar-style': 'black-translucent',
    'mobile-web-app-capable': 'yes',
    'color-scheme': 'dark light',
    'apple-mobile-web-app-title': 'Карта тривог',
    'application-name': 'Карта тривог NEPTUN',
    'msapplication-TileColor': '#0c0b0a',
    'msapplication-TileImage': '/static/icons/icon-144.png',
  },
  manifest: '/manifest.json',
  icons: {
    icon: [
      { url: '/icons/favicon-16x16.png', sizes: '16x16', type: 'image/png' },
      { url: '/icons/favicon-32x32.png', sizes: '32x32', type: 'image/png' },
    ],
    apple: [
      { url: '/icons/apple-touch-icon.png', sizes: '180x180' },
    ],
  },
};

export const viewport: Viewport = {
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: '#f5f7fa' },
    { media: '(prefers-color-scheme: dark)', color: '#0a0a0b' },
  ],
  width: 'device-width',
  initialScale: 1,
  maximumScale: 5,
  userScalable: true,
  viewportFit: 'cover',
};

// JSON-LD structured data — all 10 schemas matching original index.html
const jsonLdSchemas = [
  // 1. WebSite with SearchAction (sitelinks searchbox)
  {
    '@context': 'https://schema.org',
    '@type': 'WebSite',
    name: 'Карта шахедів і тривог України',
    alternateName: [
      'Карта тривог',
      'Мапа тривог',
      'Карта шахедів',
      'Нептун карта',
      'NEPTUN',
      'Радар шахедів',
      'Повітряна тривога онлайн',
    ],
    url: 'https://neptun.in.ua',
    potentialAction: {
      '@type': 'SearchAction',
      target: 'https://neptun.in.ua/?q={search_term_string}',
      'query-input': 'required name=search_term_string',
    },
  },
  // 2. Organization (simple)
  {
    '@context': 'https://schema.org',
    '@type': 'Organization',
    name: 'NEPTUN',
    url: 'https://neptun.in.ua',
    logo: 'https://neptun.in.ua/static/og-image.png',
  },
  // 3. WebApplication (fixed: added keywords + missing alternateName)
  {
    '@context': 'https://schema.org',
    '@type': 'WebApplication',
    name: 'Карта шахедів і тривог України — NEPTUN',
    alternateName: ['Карта шахедів', 'Карта тривог', 'Мапа тривог', 'Карта тривог онлайн', 'NEPTUN'],
    description:
      'Карта шахедів і тривог України в реальному часі. Відстежуйте повітряні тривоги, шахеди, ракети та БПЛА онлайн на інтерактивній карті.',
    url: 'https://neptun.in.ua',
    applicationCategory: 'UtilitiesApplication',
    operatingSystem: 'Web, Android, iOS',
    offers: { '@type': 'Offer', price: '0', priceCurrency: 'UAH' },
    aggregateRating: { '@type': 'AggregateRating', ratingValue: '4.9', ratingCount: '2847' },
    author: { '@type': 'Organization', name: 'NEPTUN', url: 'https://neptun.in.ua' },
    inLanguage: 'uk',
    isAccessibleForFree: true,
    keywords:
      'карта тривог, мапа тривог, карта тривог україни, повітряна тривога онлайн, повітряна тривога онлайн карта що летить, карта шахедів, нептун карта',
  },
  // 4. WebPage
  {
    '@context': 'https://schema.org',
    '@type': 'WebPage',
    name: 'Карта шахедів і тривог України онлайн — NEPTUN',
    url: 'https://neptun.in.ua/',
    description: 'Карта шахедів і тривог України в реальному часі: повітряна тривога онлайн, ракети та БПЛА.',
    isPartOf: { '@type': 'WebSite', name: 'NEPTUN', url: 'https://neptun.in.ua' },
  },
  // 5. FAQPage with 8 questions
  {
    '@context': 'https://schema.org',
    '@type': 'FAQPage',
    mainEntity: [
      {
        '@type': 'Question',
        name: 'Де подивитися карту шахедів і тривог України онлайн?',
        acceptedAnswer: {
          '@type': 'Answer',
          text: 'Карта шахедів і тривог України доступна на сайті neptun.in.ua. Це інтерактивна карта повітряних тривог в реальному часі з відстеженням шахедів, БПЛА та ракет.',
        },
      },
      {
        '@type': 'Question',
        name: 'Як працює карта шахедів і тривог NEPTUN?',
        acceptedAnswer: {
          '@type': 'Answer',
          text: 'Карта NEPTUN відображає активні повітряні тривоги та рух шахедів/БПЛА по всіх областях України в реальному часі. Дані оновлюються кожні кілька секунд.',
        },
      },
      {
        '@type': 'Question',
        name: 'Що таке радар шахедів і де його дивитися?',
        acceptedAnswer: {
          '@type': 'Answer',
          text: 'Радар шахедів — це відображення повідомлень про рух БПЛА/шахедів на карті України в реальному часі. На сайті neptun.in.ua доступна карта шахедів та тривог з оперативними оновленнями.',
        },
      },
      {
        '@type': 'Question',
        name: 'Чим відрізняється карта шахедів від карти повітряних тривог?',
        acceptedAnswer: {
          '@type': 'Answer',
          text: 'Карта повітряних тривог показує активні сирени по регіонах, а карта шахедів показує повідомлення про рух БПЛА/шахедів, маршрути та напрямок. Разом це дає повнішу картину загроз.',
        },
      },
      {
        '@type': 'Question',
        name: 'Чи є мобільний додаток карти тривог?',
        acceptedAnswer: {
          '@type': 'Answer',
          text: 'Так, додаток NEPTUN з картою тривог доступний безкоштовно в Google Play. Він надсилає push-сповіщення про тривоги у вашому регіоні.',
        },
      },
      {
        '@type': 'Question',
        name: 'Яка карта тривог найточніша?',
        acceptedAnswer: {
          '@type': 'Answer',
          text: 'NEPTUN — одна з найточніших карт тривог України. Дані надходять з офіційних джерел та оновлюються в реальному часі 24/7.',
        },
      },
      {
        '@type': 'Question',
        name: 'Як часто оновлюються дані на карті?',
        acceptedAnswer: {
          '@type': 'Answer',
          text: 'Дані оновлюються в реальному часі — карта отримує оновлення кілька разів на хвилину, щоб ви бачили актуальну ситуацію.',
        },
      },
      {
        '@type': 'Question',
        name: 'Чи працює карта тривог на мобільному?',
        acceptedAnswer: {
          '@type': 'Answer',
          text: 'Так, карта оптимізована для мобільних пристроїв і працює у браузері. Також доступний безкоштовний Android-додаток з push-сповіщеннями.',
        },
      },
      {
        '@type': 'Question',
        name: 'Де подивитися повітряну тривогу онлайн: карта, що летить?',
        acceptedAnswer: {
          '@type': 'Answer',
          text: 'На neptun.in.ua є інтерактивна карта повітряних тривог і загроз у реальному часі: видно, де оголошено тривогу, а також маркери шахедів, ракет і БПЛА з напрямком руху. Відкрийте головну сторінку або розділ «Повітряна тривога онлайн».',
        },
      },
      {
        '@type': 'Question',
        name: 'Що таке NEPTUN (нептун карта)?',
        acceptedAnswer: {
          '@type': 'Answer',
          text: 'NEPTUN (часто шукають як «нептун карта») — безкоштовна карта тривог і шахедів для України: повітряна тривога по областях, відстеження БПЛА та ракет, push у додатку.',
        },
      },
    ],
  },
  // 6. BreadcrumbList
  {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: [
      { '@type': 'ListItem', position: 1, name: 'Головна', item: 'https://neptun.in.ua' },
      { '@type': 'ListItem', position: 2, name: 'Карта тривог', item: 'https://neptun.in.ua/#map' },
    ],
  },
  // 7. HowTo (rich snippets)
  {
    '@context': 'https://schema.org',
    '@type': 'HowTo',
    name: 'Як користуватися картою тривог NEPTUN',
    description: 'Покрокова інструкція використання карти тривог України для відстеження шахедів та повітряних тривог',
    totalTime: 'PT1M',
    step: [
      { '@type': 'HowToStep', position: 1, name: 'Відкрийте карту', text: 'Перейдіть на neptun.in.ua — карта завантажиться автоматично', url: 'https://neptun.in.ua/' },
      { '@type': 'HowToStep', position: 2, name: 'Перегляньте тривоги', text: 'Червоні області — активна повітряна тривога. Іконки показують шахеди та ракети', url: 'https://neptun.in.ua/#map' },
      { '@type': 'HowToStep', position: 3, name: 'Встановіть додаток', text: 'Завантажте NEPTUN з Google Play для push-сповіщень про тривоги', url: 'https://play.google.com/store/apps/details?id=com.neptunalarm.neptun_alarm_app' },
    ],
  },
  // 8. MobileApplication (Google Play)
  {
    '@context': 'https://schema.org',
    '@type': 'MobileApplication',
    name: 'Карта тривог NEPTUN',
    operatingSystem: 'Android',
    applicationCategory: 'UtilitiesApplication',
    offers: { '@type': 'Offer', price: '0', priceCurrency: 'UAH' },
    aggregateRating: { '@type': 'AggregateRating', ratingValue: '4.9', ratingCount: '2847', bestRating: '5' },
    downloadUrl: 'https://play.google.com/store/apps/details?id=com.neptunalarm.neptun_alarm_app',
    installUrl: 'https://play.google.com/store/apps/details?id=com.neptunalarm.neptun_alarm_app',
    screenshot: 'https://neptun.in.ua/static/og-image.png',
    softwareVersion: '2.0',
    author: { '@type': 'Organization', name: 'NEPTUN' },
    description: 'Карта шахедів і тривог України в реальному часі. Відстеження шахедів, дронів, ракет. Push-сповіщення про тривоги.',
  },
  // 9. Organization (detailed — Knowledge Graph)
  {
    '@context': 'https://schema.org',
    '@type': 'Organization',
    name: 'NEPTUN',
    alternateName: ['Карта тривог NEPTUN', 'NEPTUN Alarm'],
    url: 'https://neptun.in.ua',
    logo: 'https://neptun.in.ua/static/icons/icon-512.png',
    sameAs: ['https://play.google.com/store/apps/details?id=com.neptunalarm.neptun_alarm_app'],
    contactPoint: {
      '@type': 'ContactPoint',
      contactType: 'customer support',
      availableLanguage: ['Ukrainian', 'English'],
    },
  },
  // 10. SoftwareApplication (rich snippets with featureList)
  {
    '@context': 'https://schema.org',
    '@type': 'SoftwareApplication',
    name: 'Карта шахедів і тривог України - NEPTUN',
    operatingSystem: 'Web Browser',
    applicationCategory: 'UtilitiesApplication',
    applicationSubCategory: 'Safety',
    offers: { '@type': 'Offer', price: '0', priceCurrency: 'UAH' },
    aggregateRating: { '@type': 'AggregateRating', ratingValue: '4.9', ratingCount: '3500', bestRating: '5', worstRating: '1' },
    featureList: [
      'Карта повітряних тривог в реальному часі',
      'Відстеження шахедів та дронів',
      'Push-сповіщення про тривоги',
      'Траєкторія польоту ракет',
      'Оновлення кожні 5 секунд',
    ],
  },
];

/** WebSite + Organization only — smaller HTML on marketing/static routes */
const jsonLdSchemasSlim = jsonLdSchemas.slice(0, 2);

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const h = await headers();
  const pathname = h.get('x-neptun-pathname') ?? '';
  // If middleware header is absent (some prerender edge cases), keep full assets so the map home never ships without Leaflet.
  const { leaflet: includeLeaflet, material: includeMaterial, jsonLdFull } = pathname
    ? pathnameAssetHints(pathname)
    : { leaflet: true, material: true, jsonLdFull: true };
  const schemasForPage = jsonLdFull ? jsonLdSchemas : jsonLdSchemasSlim;

  return (
    <html lang="uk" className={inter.variable} suppressHydrationWarning>
      <head>
        {/* Global theme detection — MUST run synchronously before any React script to prevent FOUC */}
        <script
          dangerouslySetInnerHTML={{
            __html: `(function(){try{var r=document.documentElement;var c=r.classList;var q=new URLSearchParams(window.location.search);var t=q.get('theme')||localStorage.getItem('theme');var p=window.location.pathname;var isApp=q.get('embed')==='1'||p.includes('export')||p.includes('map_only')||navigator.userAgent.includes('wv')||navigator.userAgent.includes('WebView');if(p.includes('export-light'))t='light';else if(p.includes('export')||p.includes('map_only'))t='dark';if(!t){if(isApp&&window.matchMedia('(prefers-color-scheme: light)').matches)t='light';else t='dark';}function applyT(theme){var light=theme==='light';if(light){c.remove('dark');c.add('theme-light');r.style.colorScheme='light';}else{c.remove('theme-light');c.add('dark');r.style.colorScheme='dark';}var m=document.querySelector('meta[name="theme-color"]');if(m)m.setAttribute('content',light?'#f5f7fa':'#0a0a0b');window.dispatchEvent(new Event('theme-change'));}applyT(t);if(isApp){window.matchMedia('(prefers-color-scheme: light)').addEventListener('change',function(e){applyT(e.matches?'light':'dark');});}if(isApp||q.get('embed')==='1')c.add('embed-mode');window.setNeptunTheme=function(theme){applyT(theme);};window.setTheme=window.setNeptunTheme;}catch(e){}})();`,
          }}
        />

        {/* Aggressively kill ALL legacy Service Workers (Old Flask mapping App cache) */}
        <script
          dangerouslySetInnerHTML={{
            __html: `if('serviceWorker' in navigator){navigator.serviceWorker.getRegistrations().then(function(rs){for(var r of rs){r.unregister()}})}`,
          }}
        />

        {/* hreflang x-default (not supported by Next.js metadata API) */}
        <link rel="alternate" hrefLang="x-default" href="https://neptun.in.ua/" />

        {/* Preconnect: gstatic for Material Icons font files (stylesheet loaded idle below). */}
        {includeMaterial ? (
          <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        ) : null}
        {/* Map tiles: DeepState-style Ukraine layer by default, OSM/Carto/Google remain available as fallbacks. */}
        {includeLeaflet ? (
          <>
            <link rel="preconnect" href="https://st1.deepstatemap.live" crossOrigin="anonymous" />
            <link rel="preconnect" href="https://a.tile.openstreetmap.org" crossOrigin="anonymous" />
            <link rel="dns-prefetch" href="https://b.tile.openstreetmap.org" />
            <link rel="dns-prefetch" href="https://c.tile.openstreetmap.org" />
            <link rel="preconnect" href="https://a.basemaps.cartocdn.com" crossOrigin="anonymous" />
            <link rel="dns-prefetch" href="https://b.basemaps.cartocdn.com" />
            <link rel="dns-prefetch" href="https://c.basemaps.cartocdn.com" />
            <link rel="preconnect" href="https://mt1.google.com" crossOrigin="anonymous" />
            <link rel="dns-prefetch" href="https://mt2.google.com" />
          </>
        ) : null}
        <link rel="dns-prefetch" href="//fonts.gstatic.com" />
        <link rel="dns-prefetch" href="//www.googletagmanager.com" />

        {includeLeaflet ? (
          <link rel="prefetch" href="/api/alarms/all" as="fetch" crossOrigin="anonymous" />
        ) : null}

        {includeLeaflet ? (
          <link
            rel="preload"
            as="image"
            href={`/shahed3.webp?${CACHE_VERSION}`}
          />
        ) : null}

        {includeLeaflet ? (
          <link rel="stylesheet" href="/vendor/leaflet/leaflet.css" />
        ) : null}

        {includeMaterial ? (
          <script
            dangerouslySetInnerHTML={{
              __html: `(function(){var h='https://fonts.googleapis.com/icon?family=Material+Icons&display=swap';function a(){if(document.querySelector('link[data-neptun-mi]'))return;var l=document.createElement('link');l.setAttribute('data-neptun-mi','1');l.rel='stylesheet';l.href=h;document.head.appendChild(l);}if(typeof requestIdleCallback==='function')requestIdleCallback(a,{timeout:4000});else setTimeout(a,800);})();`,
            }}
          />
        ) : null}

        {schemasForPage.map((schema, i) => (
          <script
            key={i}
            type="application/ld+json"
            dangerouslySetInnerHTML={{ __html: JSON.stringify(schema) }}
          />
        ))}
      </head>
      <body className="font-mono bg-[#f5f7fa] text-gray-900 dark:bg-[#050505] dark:text-white/80 antialiased selection:bg-[#ff2a5f]/30 relative transition-colors duration-300">
        {/* Body flat; атмосфера карти — MapAtmosphereOverlay у AppShell (без full-screen blur) */}
        {children}

        <DeferredGoogleAnalytics />
      </body>
    </html>
  );
}
