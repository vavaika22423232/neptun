import type { Metadata } from 'next';
import Link from 'next/link';
import Footer from '@/components/Footer';

export const metadata: Metadata = {
  title: 'Контакти — NEPTUN | Карта тривог України',
  description: 'Зв\'яжіться з командою NEPTUN. Telegram, зворотний зв\'язок, пропозиції та повідомлення про помилки.',
  alternates: {
    canonical: 'https://neptun.in.ua/contact',
  },
  openGraph: {
    type: 'website',
    url: 'https://neptun.in.ua/contact',
    title: 'Контакти — NEPTUN',
    description: 'Зв\'яжіться з командою NEPTUN.',
    images: [{ url: 'https://neptun.in.ua/api/og', width: 1200, height: 630, alt: 'Контакти NEPTUN' }],
    siteName: 'NEPTUN Карта тривог',
    locale: 'uk_UA',
  },
};

export default function ContactPage() {
  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'ContactPage',
    name: 'Контакти — NEPTUN',
    url: 'https://neptun.in.ua/contact',
    description: 'Зв\'яжіться з командою NEPTUN — карта тривог та шахедів України.',
    isPartOf: { '@type': 'WebSite', name: 'NEPTUN', url: 'https://neptun.in.ua' },
    breadcrumb: {
      '@type': 'BreadcrumbList',
      itemListElement: [
        { '@type': 'ListItem', position: 1, name: 'Головна', item: 'https://neptun.in.ua/' },
        { '@type': 'ListItem', position: 2, name: 'Контакти', item: 'https://neptun.in.ua/contact' },
      ],
    },
  };

  return (
    <div className="min-h-screen bg-[var(--surface-dim)] text-white/80 p-6 max-w-3xl mx-auto">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />

      <Link href="/" className="text-blue-400 hover:text-blue-300 text-sm mb-6 inline-block">
        &larr; Повернутися на карту
      </Link>

      <h1 className="text-3xl font-bold text-white mb-6">Контакти</h1>

      <div className="space-y-4 text-[15px] leading-relaxed">
        <p>
          Маєте питання, пропозиції або знайшли помилку? Зв&apos;яжіться з нами!
        </p>

        <div className="bg-white/5 rounded-xl p-6 mt-6">
          <h2 className="text-lg font-semibold text-white mb-3">Telegram</h2>
          <a
            href="https://t.me/+aBR79kExNQM1ZjZi"
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-400 hover:text-blue-300 text-lg"
          >
            Написати в Telegram &rarr;
          </a>
        </div>
      </div>
      <Footer />
    </div>
  );
}
