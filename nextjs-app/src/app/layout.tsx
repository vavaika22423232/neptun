import type { Metadata, Viewport } from 'next';
import { Inter } from 'next/font/google';
import Script from 'next/script';
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
    'карта шахедів, радар шахедів, карта тривог, мапа тривог, карта повітряних тривог, повітряна тривога, повітряна тривога онлайн, карта тривог україни, мапа тривог онлайн, тривога зараз, нептун карта, NEPTUN',
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
    description: 'Карта шахедів та повітряних тривог онлайн: ракети, БПЛА, КАБ.',
    images: ['https://neptun.in.ua/static/og-image.png'],
  },
  other: {
    'geo.region': 'UA',
    'geo.placename': 'Ukraine',
    language: 'Ukrainian',
    'apple-mobile-web-app-capable': 'yes',
    'apple-mobile-web-app-status-bar-style': 'black-translucent',
    'mobile-web-app-capable': 'yes',
    'color-scheme': 'dark',
    'apple-mobile-web-app-title': 'Карта тривог',
    'application-name': 'Карта тривог NEPTUN',
    'msapplication-TileColor': '#0a0e17',
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
  themeColor: '#0a0e17',
  width: 'device-width',
  initialScale: 1,
  maximumScale: 5,
  userScalable: true,
  viewportFit: 'cover',
};

// JSON-LD structured data
const jsonLd = {
  '@context': 'https://schema.org',
  '@type': 'WebApplication',
  name: 'Карта шахедів і тривог України — NEPTUN',
  alternateName: ['Карта шахедів', 'Карта тривог', 'Мапа тривог', 'NEPTUN'],
  description:
    'Карта шахедів і тривог України в реальному часі. Відстежуйте повітряні тривоги, шахеди, ракети та БПЛА онлайн на інтерактивній карті.',
  url: 'https://neptun.in.ua',
  applicationCategory: 'UtilitiesApplication',
  operatingSystem: 'Web, Android, iOS',
  offers: { '@type': 'Offer', price: '0', priceCurrency: 'UAH' },
  aggregateRating: {
    '@type': 'AggregateRating',
    ratingValue: '4.9',
    ratingCount: '2847',
  },
  author: { '@type': 'Organization', name: 'NEPTUN', url: 'https://neptun.in.ua' },
  inLanguage: 'uk',
  isAccessibleForFree: true,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="uk" className="dark">
      <head>
        {/* Preconnect to external resources */}
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link rel="preconnect" href="https://tiles.openfreemap.org" crossOrigin="anonymous" />
        <link rel="dns-prefetch" href="//www.googletagmanager.com" />

        {/* Leaflet CSS */}
        <link
          rel="stylesheet"
          href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
          integrity="sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY="
          crossOrigin=""
        />

        {/* Material Icons */}
        <link
          href="https://fonts.googleapis.com/icon?family=Material+Icons&display=block"
          rel="stylesheet"
        />

        {/* JSON-LD structured data */}
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
        />
      </head>
      <body className={`${inter.variable} font-sans bg-[#0a0e17] text-white antialiased`}>
        {children}

        {/* Google Analytics - deferred */}
        <Script
          src="https://www.googletagmanager.com/gtag/js?id=G-MW867VP8WK"
          strategy="afterInteractive"
        />
        <Script id="ga-config" strategy="afterInteractive">
          {`
            window.dataLayer = window.dataLayer || [];
            function gtag(){dataLayer.push(arguments);}
            gtag('js', new Date());
            gtag('config', 'G-MW867VP8WK');
          `}
        </Script>
      </body>
    </html>
  );
}
