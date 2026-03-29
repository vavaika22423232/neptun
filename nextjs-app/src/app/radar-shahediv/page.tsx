import type { Metadata } from 'next';
import Link from 'next/link';
import Footer from '@/components/Footer';

export const metadata: Metadata = {
  title: 'Радар шахедів — відстеження БПЛА в реальному часі | NEPTUN',
  description:
    'Радар шахедів онлайн — відстеження дронів Shahed-136/131, БПЛА та інших безпілотників на карті України в реальному часі. Траєкторії, напрямок, швидкість польоту.',
  keywords:
    'радар шахедів, радар шахедов, радар дронів, відстеження БПЛА, БПЛА трекер, шахед трекер, drone radar, shahed radar',
  alternates: {
    canonical: 'https://neptun.in.ua/radar-shahediv',
  },
  openGraph: {
    type: 'website',
    url: 'https://neptun.in.ua/radar-shahediv',
    title: 'Радар шахедів — NEPTUN',
    description: 'Відстеження шахедів, БПЛА та дронів на інтерактивній карті України. Траєкторії в реальному часі.',
    images: [{ url: 'https://neptun.in.ua/api/og', width: 1200, height: 630, alt: 'Радар шахедів — NEPTUN' }],
    siteName: 'NEPTUN Карта тривог',
    locale: 'uk_UA',
  },
};

export default function RadarShahedivPage() {
  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'WebPage',
    name: 'Радар шахедів — NEPTUN',
    url: 'https://neptun.in.ua/radar-shahediv',
    description: 'Радар шахедів онлайн — відстеження БПЛА, дронів Shahed та інших безпілотників на карті України.',
    isPartOf: { '@type': 'WebSite', name: 'NEPTUN', url: 'https://neptun.in.ua' },
    breadcrumb: {
      '@type': 'BreadcrumbList',
      itemListElement: [
        { '@type': 'ListItem', position: 1, name: 'Головна', item: 'https://neptun.in.ua' },
        { '@type': 'ListItem', position: 2, name: 'Радар шахедів', item: 'https://neptun.in.ua/radar-shahediv' },
      ],
    },
  };

  return (
    <div className="min-h-screen bg-[var(--surface-dim)] text-white/80 p-6 max-w-3xl mx-auto">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />

      <Link href="/" className="text-blue-400 hover:text-blue-300 text-sm mb-6 inline-block">
        &larr; Відкрити карту
      </Link>

      <h1 className="text-3xl font-bold text-white mb-4">
        Радар шахедів — відстеження БПЛА в реальному часі
      </h1>

      <p className="text-lg text-white/70 mb-6">
        Радар шахедів NEPTUN показує рух безпілотних літальних апаратів над Україною в реальному часі.
        Бачте траєкторії польоту, напрямок руху та точки запуску шахедів прямо на карті.
      </p>

      <Link
        href="/"
        className="inline-flex items-center gap-2 bg-blue-500 hover:bg-blue-600 text-white px-6 py-3 rounded-xl font-medium transition-colors mb-8"
      >
        Відкрити радар шахедів &rarr;
      </Link>

      <article className="text-white/70 leading-relaxed space-y-6">
        <section>
          <h2 className="text-xl font-semibold text-white/90 mb-3">Що таке радар шахедів?</h2>
          <p>
            <strong className="text-white">Радар шахедів</strong> — це система відстеження безпілотних літальних апаратів (БПЛА)
            на інтерактивній <Link href="/karta-shahediv" className="text-blue-400 hover:underline">карті шахедів</Link>. На відміну від
            звичайного радару, який використовує радіохвилі, наш радар працює на основі аналізу повідомлень
            з офіційних Telegram-каналів та моніторингових груп. Результат — точне відображення БПЛА на карті
            з траєкторіями та напрямком польоту.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-white/90 mb-3">Як працює радар шахедів NEPTUN?</h2>
          <ol className="list-decimal pl-6 space-y-3">
            <li>
              <strong className="text-white">Збір даних</strong> — система автоматично моніторить десятки Telegram-каналів ОВА
              та перевірених джерел цілодобово
            </li>
            <li>
              <strong className="text-white">ШІ-аналіз</strong> — кожне повідомлення аналізується штучним інтелектом, який
              визначає тип загрози, місцезнаходження, кількість та напрямок
            </li>
            <li>
              <strong className="text-white">Геокодування</strong> — назви населених пунктів конвертуються в координати
              через базу з 30 000+ місць України
            </li>
            <li>
              <strong className="text-white">Відображення</strong> — загроза з&apos;являється на карті за 5-10 секунд
              з іконкою типу (шахед, ракета, БПЛА) та стрілкою напрямку
            </li>
            <li>
              <strong className="text-white">Оновлення</strong> — наступні повідомлення про ту ж загрозу оновлюють
              маркер на карті (координати, напрямок), а не створюють дублікат
            </li>
          </ol>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-white/90 mb-3">Що показує радар?</h2>
          <div className="grid sm:grid-cols-2 gap-4">
            <div className="bg-white/5 rounded-xl p-4">
              <h3 className="font-medium text-white mb-1">📍 Місцезнаходження</h3>
              <p className="text-sm">Точне розташування шахеда або групи шахедів на карті з прив&apos;язкою до населеного пункту.</p>
            </div>
            <div className="bg-white/5 rounded-xl p-4">
              <h3 className="font-medium text-white mb-1">➡️ Напрямок</h3>
              <p className="text-sm">Курс польоту — куди рухається загроза. Стрілка на маркері показує напрямок.</p>
            </div>
            <div className="bg-white/5 rounded-xl p-4">
              <h3 className="font-medium text-white mb-1">📊 Кількість</h3>
              <p className="text-sm">Скільки шахедів або БПЛА зафіксовано в групі. Число відображається на маркері.</p>
            </div>
            <div className="bg-white/5 rounded-xl p-4">
              <h3 className="font-medium text-white mb-1">🎯 Точка запуску</h3>
              <p className="text-sm">Звідки запущено: Чорне море, Крим, Краснодарський край, Курськ та інші регіони.</p>
            </div>
          </div>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-white/90 mb-3">Типи БПЛА на радарі</h2>
          <ul className="list-disc pl-6 space-y-2">
            <li>
              <strong className="text-white">Shahed-136/131</strong> — іранські дрони-камікадзе. Швидкість ~150-180 км/год.
              Основна загроза при масованих нічних атаках
            </li>
            <li>
              <strong className="text-white">Розвідувальні БПЛА</strong> — використовуються для розвідки та коригування.
              Зазвичай поодинокі
            </li>
            <li>
              <strong className="text-white">БПЛА невстановленого типу</strong> — безпілотники, тип яких не ідентифіковано
              на момент виявлення
            </li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-white/90 mb-3">Де дивитися радар шахедів?</h2>
          <p>
            Радар шахедів доступний безкоштовно на <Link href="/" className="text-blue-400 hover:underline">neptun.in.ua</Link>.
            Для отримання push-сповіщень про загрози у вашому регіоні встановіть мобільний додаток:
          </p>
          <div className="flex flex-wrap gap-3 mt-3">
            <a
              href="https://play.google.com/store/apps/details?id=com.neptunalarm.neptun_alarm_app"
              className="inline-flex items-center gap-2 bg-green-500/10 text-green-400 px-4 py-2 rounded-lg hover:bg-green-500/20 transition-colors"
              target="_blank" rel="noopener noreferrer"
            >
              Android (Google Play)
            </a>
            <a
              href="https://apps.apple.com/ua/app/%D0%BA%D0%B0%D1%80%D1%82%D0%B0-%D1%82%D1%80%D0%B8%D0%B2%D0%BE%D0%B3-dron-alerts/id6758108122?l=uk"
              className="inline-flex items-center gap-2 bg-blue-500/10 text-blue-400 px-4 py-2 rounded-lg hover:bg-blue-500/20 transition-colors"
              target="_blank" rel="noopener noreferrer"
            >
              iOS (App Store)
            </a>
          </div>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-white/90 mb-3">Пов&apos;язані сторінки</h2>
          <ul className="space-y-2">
            <li>
              <Link href="/karta-shahediv" className="text-blue-400 hover:underline">Карта шахедів</Link>
              {' — '}інтерактивна мапа з відстеженням шахедів
            </li>
            <li>
              <Link href="/karta-tryvoh" className="text-blue-400 hover:underline">Карта тривог</Link>
              {' — '}повітряна тривога по всіх областях України
            </li>
            <li>
              <Link href="/faq" className="text-blue-400 hover:underline">FAQ</Link>
              {' — '}часті питання про карту тривог NEPTUN
            </li>
          </ul>
        </section>
      </article>

      <Footer />
    </div>
  );
}
