import { Suspense } from 'react';
import type { Metadata } from 'next';
import AviationClient from './AviationClient';

export const metadata: Metadata = {
  title: 'Авіаційна карта України — радар повітряних суден | NEPTUN',
  description:
    'Онлайн авіаційна карта України: цивільні та військові повітряні судна, зони обмеження польотів, NOTAM. Моніторинг повітряного простору в реальному часі.',
  keywords:
    'авіаційна карта, авіарадар Україна, повітряний простір, NOTAM, повітряні судна онлайн, авіація',
  alternates: {
    canonical: 'https://neptun.in.ua/aviation',
  },
  openGraph: {
    type: 'website',
    url: 'https://neptun.in.ua/aviation',
    title: 'Авіаційна карта України — NEPTUN',
    description:
      'Онлайн авіаційна карта: повітряні судна, зони обмеження, NOTAM.',
    siteName: 'NEPTUN Карта тривог',
    locale: 'uk_UA',
  },
};

export default function AviationPage() {
  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'WebPage',
    name: 'Авіаційна карта України — NEPTUN',
    url: 'https://neptun.in.ua/aviation',
    description: 'Онлайн авіаційна карта України: цивільні та військові повітряні судна, зони обмеження польотів, NOTAM.',
    isPartOf: { '@type': 'WebSite', name: 'NEPTUN', url: 'https://neptun.in.ua' },
    breadcrumb: {
      '@type': 'BreadcrumbList',
      itemListElement: [
        { '@type': 'ListItem', position: 1, name: 'Головна', item: 'https://neptun.in.ua/' },
        { '@type': 'ListItem', position: 2, name: 'Авіаційна карта', item: 'https://neptun.in.ua/aviation' },
      ],
    },
  };

  return (
    <>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />
      <Suspense fallback={<div className="w-full h-full bg-[var(--surface)]" />}>
        <AviationClient />
      </Suspense>
    </>
  );
}
