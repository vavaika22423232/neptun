import type { Metadata } from 'next';
import Link from 'next/link';
import Footer from '@/components/Footer';

export const metadata: Metadata = {
  title: 'Віджет карти тривог для вашого сайту — NEPTUN Embed',
  description:
    'Вбудуйте карту повітряних тривог NEPTUN на ваш сайт або блог. Безкоштовний iframe-віджет з картою тривог України в реальному часі.',
  keywords:
    'віджет тривог, embed карта тривог, iframe карта тривог, віджет для сайту, карта тривог для блогу, API карта тривог',
  alternates: {
    canonical: 'https://neptun.in.ua/embed',
  },
  openGraph: {
    type: 'website',
    url: 'https://neptun.in.ua/embed',
    title: 'Віджет карти тривог для вашого сайту — NEPTUN',
    description: 'Безкоштовний iframe-віджет з картою повітряних тривог України в реальному часі.',
    images: [{ url: 'https://neptun.in.ua/api/og', width: 1200, height: 630, alt: 'NEPTUN Embed' }],
    siteName: 'NEPTUN Карта тривог',
    locale: 'uk_UA',
  },
};

export default function EmbedPage() {
  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'WebPage',
    name: 'Віджет карти тривог — NEPTUN Embed',
    url: 'https://neptun.in.ua/embed',
    description: 'Вбудуйте карту повітряних тривог NEPTUN на ваш сайт або блог безкоштовно.',
    isPartOf: { '@type': 'WebSite', name: 'NEPTUN', url: 'https://neptun.in.ua' },
    breadcrumb: {
      '@type': 'BreadcrumbList',
      itemListElement: [
        { '@type': 'ListItem', position: 1, name: 'Головна', item: 'https://neptun.in.ua/' },
        { '@type': 'ListItem', position: 2, name: 'Віджет', item: 'https://neptun.in.ua/embed' },
      ],
    },
  };

  const iframeCode = `<iframe
  src="https://neptun.in.ua/"
  width="100%"
  height="600"
  style="border: none; border-radius: 12px;"
  loading="lazy"
  title="Карта тривог України — NEPTUN"
  allow="geolocation"
></iframe>`;

  const iframeCodeCompact = `<iframe
  src="https://neptun.in.ua/"
  width="400"
  height="500"
  style="border: 1px solid #1a2030; border-radius: 8px;"
  loading="lazy"
  title="Карта тривог — NEPTUN"
></iframe>`;

  const linkBackHtml = `<p style="font-size: 12px; text-align: center; margin-top: 4px;">
  <a href="https://neptun.in.ua/" target="_blank" rel="noopener">
    Карта тривог NEPTUN
  </a>
</p>`;

  return (
    <div className="min-h-screen bg-[var(--surface-dim)] text-white/80 p-6 max-w-3xl mx-auto">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />

      <Link href="/" className="text-blue-400 hover:text-blue-300 text-sm mb-6 inline-block">
        &larr; Повернутися на карту
      </Link>

      <h1 className="text-3xl font-bold text-white mb-2">
        Віджет карти тривог для вашого сайту
      </h1>
      <p className="text-white/50 text-sm mb-8">
        Вбудуйте карту повітряних тривог NEPTUN на ваш сайт, блог або форум безкоштовно
      </p>

      <div className="space-y-8 text-[15px] leading-relaxed">
        {/* Full-width embed */}
        <section>
          <h2 className="text-xl font-semibold text-white mb-3">Повноширинний варіант</h2>
          <p className="mb-3">
            Ідеально підходить для вбудовування на повну ширину сторінки. Карта автоматично
            адаптується під розмір контейнера.
          </p>
          <div className="bg-[#0e1420] rounded-xl p-4 border border-white/5 overflow-x-auto">
            <pre className="text-sm text-[#36e4ff] whitespace-pre">{iframeCode}</pre>
          </div>
          <p className="mt-2 text-sm text-white/40">
            Виділіть код і скопіюйте (Ctrl+C / ⌘+C)
          </p>
        </section>

        {/* Compact / sidebar embed */}
        <section>
          <h2 className="text-xl font-semibold text-white mb-3">Компактний варіант (сайдбар)</h2>
          <p className="mb-3">
            Для бічної панелі або компактних блоків. Фіксований розмір 400×500 пікселів.
          </p>
          <div className="bg-[#0e1420] rounded-xl p-4 border border-white/5 overflow-x-auto">
            <pre className="text-sm text-[#36e4ff] whitespace-pre">{iframeCodeCompact}</pre>
          </div>
        </section>

        {/* Link back -->  */}
        <section>
          <h2 className="text-xl font-semibold text-white mb-3">Посилання (рекомендовано)</h2>
          <p className="mb-3">
            Додайте посилання під віджетом для кращої індексації обох сайтів. Це допомагає
            вашим відвідувачам знайти повну версію карти тривог.
          </p>
          <div className="bg-[#0e1420] rounded-xl p-4 border border-white/5 overflow-x-auto">
            <pre className="text-sm text-[#36e4ff] whitespace-pre">{linkBackHtml}</pre>
          </div>
        </section>

        {/* Live preview - shown as placeholder to avoid SSG loops */}
        <section>
          <h2 className="text-xl font-semibold text-white mb-3">Попередній перегляд</h2>
          <div className="bg-white/5 rounded-xl p-4 border border-white/10">
            <div className="bg-[#0e1420] rounded-lg w-full h-[400px] flex items-center justify-center text-white/30 text-sm">
              Відкрийте{' '}
              <a href="https://neptun.in.ua/" target="_blank" rel="noopener noreferrer" className="text-blue-400 underline mx-1">
                neptun.in.ua
              </a>{' '}
              щоб побачити карту в дії
            </div>
            <p className="text-center text-xs text-white/40 mt-2">
              <a href="https://neptun.in.ua/" target="_blank" rel="noopener noreferrer" className="text-blue-400/60 hover:text-blue-400">
                Карта тривог NEPTUN
              </a>
            </p>
          </div>
        </section>

        {/* Instructions */}
        <section>
          <h2 className="text-xl font-semibold text-white mb-3">Як вбудувати</h2>
          <ol className="list-decimal pl-6 space-y-2">
            <li>Скопіюйте код iframe з варіанту вище (повноширинний або компактний)</li>
            <li>Вставте код у HTML вашого сайту або редактор блогу</li>
            <li>За бажанням додайте посилання під віджетом</li>
            <li>Карта буде автоматично оновлюватися в реальному часі</li>
          </ol>
        </section>

        {/* Supported platforms */}
        <section>
          <h2 className="text-xl font-semibold text-white mb-3">Підтримувані платформи</h2>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            {['WordPress', 'Blogger', 'Wix', 'Squarespace', 'Tilda', 'Hugo', 'Jekyll', 'Ghost', 'Webflow'].map((p) => (
              <div key={p} className="bg-white/5 rounded-lg py-2 px-3 text-center text-sm text-white/70">
                {p}
              </div>
            ))}
          </div>
          <p className="text-sm text-white/40 mt-3">
            Працює на будь-якій платформі, що підтримує HTML iframe.
          </p>
        </section>

        {/* Terms */}
        <section className="border-t border-white/5 pt-6 text-sm text-white/40">
          <h2 className="text-base font-medium text-white/60 mb-2">Умови використання віджету</h2>
          <ul className="list-disc pl-6 space-y-1">
            <li>Віджет безкоштовний для комерційного та некомерційного використання</li>
            <li>Просимо зберігати посилання на neptun.in.ua</li>
            <li>Заборонено модифікувати вміст iframe або видаляти бренд NEPTUN</li>
            <li>Ми не гарантуємо 100% безперебійну роботу віджету</li>
          </ul>
        </section>
      </div>

      <Footer />
    </div>
  );
}
