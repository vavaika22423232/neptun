import type { Metadata } from 'next';
import Link from 'next/link';
import Footer from '@/components/Footer';

export const metadata: Metadata = {
  title: 'Як налаштувати push-сповіщення про тривоги — NEPTUN додаток | NEPTUN',
  description:
    'Покрокова інструкція: завантажити NEPTUN на Android/iOS, обрати регіон, налаштувати типи сповіщень та звук тривоги. Отримуйте push-сповіщення про повітряні тривоги.',
  keywords:
    'push сповіщення тривоги, налаштувати тривогу телефон, NEPTUN додаток інструкція, сповіщення про шахеди',
  alternates: { canonical: 'https://neptun.in.ua/blog/yak-nalashtuvatу-push-spovishchennya' },
  openGraph: {
    type: 'article',
    url: 'https://neptun.in.ua/blog/yak-nalashtuvatу-push-spovishchennya',
    title: 'Як налаштувати push-сповіщення NEPTUN',
    description: 'Покрокова інструкція налаштування push-сповіщень про повітряні тривоги.',
    images: [{ url: 'https://neptun.in.ua/api/og', width: 1200, height: 630 }],
    siteName: 'NEPTUN',
    locale: 'uk_UA',
  },
};

export default function Article() {
  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'BlogPosting',
    headline: 'Як налаштувати push-сповіщення про тривоги — NEPTUN додаток',
    url: 'https://neptun.in.ua/blog/yak-nalashtuvatу-push-spovishchennya',
    datePublished: '2025-01-28',
    dateModified: '2025-01-28',
    author: { '@type': 'Organization', name: 'NEPTUN', url: 'https://neptun.in.ua' },
    publisher: { '@type': 'Organization', name: 'NEPTUN', url: 'https://neptun.in.ua' },
    inLanguage: 'uk',
    mainEntityOfPage: 'https://neptun.in.ua/blog/yak-nalashtuvatу-push-spovishchennya',
    breadcrumb: {
      '@type': 'BreadcrumbList',
      itemListElement: [
        { '@type': 'ListItem', position: 1, name: 'Головна', item: 'https://neptun.in.ua/' },
        { '@type': 'ListItem', position: 2, name: 'Блог', item: 'https://neptun.in.ua/blog' },
        { '@type': 'ListItem', position: 3, name: 'Push-сповіщення', item: 'https://neptun.in.ua/blog/yak-nalashtuvatу-push-spovishchennya' },
      ],
    },
  };

  return (
    <div className="min-h-screen bg-[var(--surface-dim)] text-white/80 p-6 max-w-3xl mx-auto">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />

      <nav className="text-sm text-white/40 mb-6 flex items-center gap-2">
        <Link href="/" className="text-blue-400 hover:text-blue-300">Головна</Link>
        <span>/</span>
        <Link href="/blog" className="text-blue-400 hover:text-blue-300">Блог</Link>
        <span>/</span>
        <span className="text-white/60">Push-сповіщення</span>
      </nav>

      <article>
        <div className="text-xs text-white/40 mb-3">
          <time dateTime="2025-01-28">28 січня 2025</time> · 5 хв читання
        </div>

        <h1 className="text-3xl font-bold text-white mb-6">
          Як налаштувати push-сповіщення про тривоги — NEPTUN додаток
        </h1>

        <div className="space-y-4 text-[15px] leading-relaxed">
          <p>
            Push-сповіщення — це найшвидший спосіб дізнатися про повітряну тривогу у вашому регіоні.
            Додаток NEPTUN надсилає сповіщення навіть коли телефон заблоковано та додаток закритий.
            У цій інструкції розповімо, як встановити та налаштувати все за 2 хвилини.
          </p>

          <h2 className="text-xl font-semibold text-white mt-8">Крок 1: Завантажте додаток</h2>
          <p>Додаток NEPTUN безкоштовний та доступний для обох платформ:</p>
          <div className="flex flex-wrap gap-4 my-4">
            <a
              href="https://play.google.com/store/apps/details?id=com.neptunalarm.neptun_alarm_app"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-5 py-3 bg-white/10 hover:bg-white/15 rounded-xl text-white font-medium transition-colors no-underline"
            >
              ▶ Google Play (Android)
            </a>
            <a
              href="https://apps.apple.com/ua/app/%D0%BA%D0%B0%D1%80%D1%82%D0%B0-%D1%82%D1%80%D0%B8%D0%B2%D0%BE%D0%B3-dron-alerts/id6758108122?l=uk"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-5 py-3 bg-white/10 hover:bg-white/15 rounded-xl text-white font-medium transition-colors no-underline"
            >
              🍎 App Store (iOS)
            </a>
          </div>

          <h2 className="text-xl font-semibold text-white mt-8">Крок 2: Відкрийте додаток та оберіть регіон</h2>
          <p>
            При першому запуску додаток запропонує обрати ваш регіон. Це визначає, про які тривоги ви
            будете отримувати push-сповіщення. Ви можете обрати:
          </p>
          <ul className="list-disc pl-6 space-y-1.5">
            <li><strong className="text-white/90">Одну область</strong> — отримуєте лише тривоги вашого регіону</li>
            <li><strong className="text-white/90">Кілька областей</strong> — корисно, якщо подорожуєте або маєте рідних в інших регіонах</li>
            <li><strong className="text-white/90">Всю Україну</strong> — всі тривоги по всій країні</li>
          </ul>

          <div className="bg-[#36e4ff]/5 border border-[#36e4ff]/10 rounded-xl p-4 my-4">
            <p className="text-[#36e4ff] text-sm">
              💡 Рекомендуємо обрати 1-2 регіони, де ви зараз знаходитесь. Занадто багато сповіщень
              можуть втомлювати та знижувати вашу увагу до реальних загроз.
            </p>
          </div>

          <h2 className="text-xl font-semibold text-white mt-8">Крок 3: Дозвольте сповіщення</h2>
          <p>
            Операційна система попросить дозволити NEPTUN надсилати сповіщення. Обов&rsquo;язково
            натисніть <strong className="text-white">&ldquo;Дозволити&rdquo;</strong> — без цього push-сповіщення не працюватимуть.
          </p>

          <h3 className="text-lg font-medium text-white mt-6">На Android:</h3>
          <ul className="list-disc pl-6 space-y-1.5">
            <li>Натисніть &ldquo;Дозволити&rdquo; у спливаючому вікні</li>
            <li>Якщо випадково відхилили — відкрийте Налаштування → Додатки → NEPTUN → Сповіщення → Увімкнути</li>
            <li>Вимкніть оптимізацію батареї для NEPTUN (Налаштування → Батарея → NEPTUN → Без обмежень)</li>
          </ul>

          <h3 className="text-lg font-medium text-white mt-6">На iOS (iPhone):</h3>
          <ul className="list-disc pl-6 space-y-1.5">
            <li>Натисніть &ldquo;Дозволити&rdquo; у спливаючому вікні</li>
            <li>Якщо відхилили — відкрийте Налаштування → NEPTUN → Сповіщення → Увімкнути</li>
            <li>Увімкніть &ldquo;Термінові сповіщення&rdquo; (Critical Alerts) для максимальної надійності</li>
          </ul>

          <h2 className="text-xl font-semibold text-white mt-8">Крок 4: Налаштуйте типи сповіщень</h2>
          <p>У додатку NEPTUN ви можете обрати, про які типи загроз отримувати сповіщення:</p>
          <ul className="list-disc pl-6 space-y-1.5">
            <li><strong className="text-white/90">Повітряна тривога</strong> — початок та відбій тривоги (рекомендовано увімкнути)</li>
            <li><strong className="text-white/90">Шахеди</strong> — рух БПЛА у вашому напрямку</li>
            <li><strong className="text-white/90">Ракети</strong> — інформація про ракетну загрозу</li>
          </ul>

          <h2 className="text-xl font-semibold text-white mt-8">Крок 5: Перевірте роботу</h2>
          <p>
            Після налаштування дочекайтесь наступної тривоги у вашому регіоні — ви повинні отримати
            push-сповіщення на телефон. Також можете перевірити статус тривоги прямо зараз на{' '}
            <Link href="/" className="text-blue-400 hover:text-blue-300">карті тривог NEPTUN</Link>.
          </p>

          <h2 className="text-xl font-semibold text-white mt-8">Вирішення проблем</h2>
          <div className="space-y-4">
            <div className="bg-white/5 rounded-xl p-4">
              <h3 className="text-white font-medium mb-1">Не приходять сповіщення?</h3>
              <p className="text-sm text-white/60">
                Перевірте: 1) Сповіщення дозволені в налаштуваннях телефону, 2) Оптимізація батареї
                вимкнена для NEPTUN, 3) Обраний регіон відповідає вашому місцеположенню.
              </p>
            </div>
            <div className="bg-white/5 rounded-xl p-4">
              <h3 className="text-white font-medium mb-1">Сповіщення приходять із затримкою?</h3>
              <p className="text-sm text-white/60">
                Вимкніть режим &ldquo;Не турбувати&rdquo; та енергозбереження. На деяких Android-пристроях
                (Xiaomi, Huawei) потрібно додатково дозволити автозапуск додатку.
              </p>
            </div>
            <div className="bg-white/5 rounded-xl p-4">
              <h3 className="text-white font-medium mb-1">Як змінити регіон?</h3>
              <p className="text-sm text-white/60">
                Відкрийте додаток → Налаштування (іконка шестерні) → Регіони → Оберіть новий регіон.
              </p>
            </div>
          </div>

          <h2 className="text-xl font-semibold text-white mt-8">Також на вебі</h2>
          <p>
            Якщо ви не хочете встановлювати додаток, ви можете відстежувати тривоги через{' '}
            <Link href="/" className="text-blue-400 hover:text-blue-300">веб-версію NEPTUN</Link> у
            браузері вашого телефону. Веб-версія також оновлюється в реальному часі.
          </p>
        </div>
      </article>

      <div className="mt-8 pt-6 border-t border-white/10">
        <Link href="/blog" className="text-blue-400 hover:text-blue-300 text-sm">
          &larr; Усі статті блогу
        </Link>
      </div>

      <Footer />
    </div>
  );
}
