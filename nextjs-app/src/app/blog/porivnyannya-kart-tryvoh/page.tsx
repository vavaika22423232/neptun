import type { Metadata } from 'next';
import Link from 'next/link';
import Footer from '@/components/Footer';

export const metadata: Metadata = {
  title: 'Порівняння карт тривог України 2025 — NEPTUN vs інші сервіси',
  description:
    'Об\'єктивне порівняння карт тривог України: NEPTUN, alerts.in.ua, «Повітряна тривога», Air Alert. Швидкість оновлення, функціонал, мобільні додатки, зручність.',
  keywords:
    'порівняння карт тривог, яка карта тривог краща, NEPTUN vs alerts, огляд карт тривог 2025, карта тривог рейтинг',
  alternates: { canonical: 'https://neptun.in.ua/blog/porivnyannya-kart-tryvoh' },
  openGraph: {
    type: 'article',
    url: 'https://neptun.in.ua/blog/porivnyannya-kart-tryvoh',
    title: 'Порівняння карт тривог України 2025',
    description: 'Який сервіс карти тривог обрати? Об\'єктивне порівняння основних платформ.',
    images: [{ url: 'https://neptun.in.ua/api/og', width: 1200, height: 630 }],
    siteName: 'NEPTUN',
    locale: 'uk_UA',
  },
};

export default function Article() {
  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'BlogPosting',
    headline: 'Порівняння карт тривог України 2025 — NEPTUN vs інші сервіси',
    url: 'https://neptun.in.ua/blog/porivnyannya-kart-tryvoh',
    datePublished: '2025-01-20',
    dateModified: '2025-01-20',
    author: { '@type': 'Organization', name: 'NEPTUN', url: 'https://neptun.in.ua' },
    publisher: { '@type': 'Organization', name: 'NEPTUN', url: 'https://neptun.in.ua' },
    inLanguage: 'uk',
    mainEntityOfPage: 'https://neptun.in.ua/blog/porivnyannya-kart-tryvoh',
    breadcrumb: {
      '@type': 'BreadcrumbList',
      itemListElement: [
        { '@type': 'ListItem', position: 1, name: 'Головна', item: 'https://neptun.in.ua/' },
        { '@type': 'ListItem', position: 2, name: 'Блог', item: 'https://neptun.in.ua/blog' },
        { '@type': 'ListItem', position: 3, name: 'Порівняння карт', item: 'https://neptun.in.ua/blog/porivnyannya-kart-tryvoh' },
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
        <span className="text-white/60">Порівняння карт тривог</span>
      </nav>

      <article>
        <div className="text-xs text-white/40 mb-3">
          <time dateTime="2025-01-20">20 січня 2025</time> · 6 хв читання
        </div>

        <h1 className="text-3xl font-bold text-white mb-6">
          Порівняння карт тривог України 2025 — NEPTUN vs інші сервіси
        </h1>

        <div className="space-y-4 text-[15px] leading-relaxed">
          <p>
            В Україні існує кілька популярних сервісів для моніторингу повітряних тривог. У цій статті
            ми об&rsquo;єктивно порівняємо їхні можливості, щоб ви могли обрати оптимальний інструмент
            для своєї безпеки.
          </p>

          {/* Comparison table */}
          <h2 className="text-xl font-semibold text-white mt-8">Порівняльна таблиця</h2>
          <div className="overflow-x-auto my-4">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/10 text-white/50">
                  <th className="py-2 px-3 text-left font-medium">Параметр</th>
                  <th className="py-2 px-3 text-center font-medium text-[#36e4ff]">NEPTUN</th>
                  <th className="py-2 px-3 text-center font-medium">alerts.in.ua</th>
                  <th className="py-2 px-3 text-center font-medium">Повітряна тривога</th>
                </tr>
              </thead>
              <tbody>
                <tr className="border-b border-white/5">
                  <td className="py-2 px-3">Оновлення</td>
                  <td className="py-2 px-3 text-center text-green-400">5 сек</td>
                  <td className="py-2 px-3 text-center">~30 сек</td>
                  <td className="py-2 px-3 text-center">~10 сек</td>
                </tr>
                <tr className="border-b border-white/5">
                  <td className="py-2 px-3">Карта шахедів</td>
                  <td className="py-2 px-3 text-center text-green-400">✓ з траєкторіями</td>
                  <td className="py-2 px-3 text-center text-white/40">✗</td>
                  <td className="py-2 px-3 text-center text-white/40">✗</td>
                </tr>
                <tr className="border-b border-white/5">
                  <td className="py-2 px-3">ШІ-аналіз</td>
                  <td className="py-2 px-3 text-center text-green-400">✓</td>
                  <td className="py-2 px-3 text-center text-white/40">✗</td>
                  <td className="py-2 px-3 text-center text-white/40">✗</td>
                </tr>
                <tr className="border-b border-white/5">
                  <td className="py-2 px-3">Push-сповіщення</td>
                  <td className="py-2 px-3 text-center text-green-400">✓</td>
                  <td className="py-2 px-3 text-center text-green-400">✓</td>
                  <td className="py-2 px-3 text-center text-green-400">✓</td>
                </tr>
                <tr className="border-b border-white/5">
                  <td className="py-2 px-3">Android додаток</td>
                  <td className="py-2 px-3 text-center text-green-400">✓</td>
                  <td className="py-2 px-3 text-center text-green-400">✓</td>
                  <td className="py-2 px-3 text-center text-green-400">✓</td>
                </tr>
                <tr className="border-b border-white/5">
                  <td className="py-2 px-3">iOS додаток</td>
                  <td className="py-2 px-3 text-center text-green-400">✓</td>
                  <td className="py-2 px-3 text-center text-white/40">✗</td>
                  <td className="py-2 px-3 text-center text-green-400">✓</td>
                </tr>
                <tr className="border-b border-white/5">
                  <td className="py-2 px-3">Авіаційна карта</td>
                  <td className="py-2 px-3 text-center text-green-400">✓</td>
                  <td className="py-2 px-3 text-center text-white/40">✗</td>
                  <td className="py-2 px-3 text-center text-white/40">✗</td>
                </tr>
                <tr className="border-b border-white/5">
                  <td className="py-2 px-3">Деталізація по районах</td>
                  <td className="py-2 px-3 text-center text-green-400">✓</td>
                  <td className="py-2 px-3 text-center text-green-400">✓</td>
                  <td className="py-2 px-3 text-center">Області</td>
                </tr>
                <tr className="border-b border-white/5">
                  <td className="py-2 px-3">Безкоштовно</td>
                  <td className="py-2 px-3 text-center text-green-400">✓</td>
                  <td className="py-2 px-3 text-center text-green-400">✓</td>
                  <td className="py-2 px-3 text-center text-green-400">✓</td>
                </tr>
                <tr className="border-b border-white/5">
                  <td className="py-2 px-3">Темна тема</td>
                  <td className="py-2 px-3 text-center text-green-400">✓</td>
                  <td className="py-2 px-3 text-center text-white/40">Часткова</td>
                  <td className="py-2 px-3 text-center text-white/40">✗</td>
                </tr>
              </tbody>
            </table>
          </div>

          {/* Detailed reviews */}
          <h2 className="text-xl font-semibold text-white mt-8">NEPTUN — карта тривог та шахедів</h2>
          <div className="bg-[#36e4ff]/5 border border-[#36e4ff]/10 rounded-xl p-5">
            <p className="mb-3">
              <strong className="text-white">NEPTUN</strong> — найновіший сервіс у цьому порівнянні, але з найширшим
              функціоналом. Головна перевага — <strong className="text-white">карта шахедів з траєкторіями</strong>,
              якої немає в жодного конкурента. ШІ-аналіз повідомлень дозволяє автоматично визначати тип загрози
              та напрямок руху.
            </p>
            <div className="flex flex-wrap gap-2 mt-2">
              <span className="text-xs px-2 py-0.5 bg-green-500/10 text-green-400 rounded-md">Швидкість 5с</span>
              <span className="text-xs px-2 py-0.5 bg-green-500/10 text-green-400 rounded-md">Шахеди</span>
              <span className="text-xs px-2 py-0.5 bg-green-500/10 text-green-400 rounded-md">ШІ</span>
              <span className="text-xs px-2 py-0.5 bg-green-500/10 text-green-400 rounded-md">iOS + Android</span>
            </div>
          </div>

          <h2 className="text-xl font-semibold text-white mt-8">alerts.in.ua</h2>
          <div className="bg-white/5 rounded-xl p-5">
            <p className="mb-3">
              Один з перших сервісів карти тривог в Україні (працює з 2022 року). Простий інтерфейс,
              показує статус тривоги по областях та районах. Має Android-додаток з push-сповіщеннями.
              Не має карти шахедів, авіаційної карти чи ШІ-аналізу.
            </p>
            <div className="flex flex-wrap gap-2 mt-2">
              <span className="text-xs px-2 py-0.5 bg-white/10 text-white/50 rounded-md">Простий</span>
              <span className="text-xs px-2 py-0.5 bg-white/10 text-white/50 rounded-md">Android</span>
              <span className="text-xs px-2 py-0.5 bg-white/10 text-white/50 rounded-md">З 2022</span>
            </div>
          </div>

          <h2 className="text-xl font-semibold text-white mt-8">&ldquo;Повітряна тривога&rdquo; (офіційний додаток)</h2>
          <div className="bg-white/5 rounded-xl p-5">
            <p className="mb-3">
              Офіційний додаток від ДСНС/Мінцифри. Головна перевага — <strong className="text-white">офіційний статус</strong>.
              Надсилає сповіщення та відображає тривоги по областях. Інтерфейс базовий,
              без додаткового функціоналу (шахеди, траєкторії).
            </p>
            <div className="flex flex-wrap gap-2 mt-2">
              <span className="text-xs px-2 py-0.5 bg-white/10 text-white/50 rounded-md">Офіційний</span>
              <span className="text-xs px-2 py-0.5 bg-white/10 text-white/50 rounded-md">iOS + Android</span>
              <span className="text-xs px-2 py-0.5 bg-white/10 text-white/50 rounded-md">ДСНС</span>
            </div>
          </div>

          <h2 className="text-xl font-semibold text-white mt-8">Який сервіс обрати?</h2>
          <div className="space-y-3 mt-3">
            <div className="bg-white/5 rounded-xl p-4">
              <h3 className="text-white font-medium mb-1">Для максимальної інформативності</h3>
              <p className="text-sm text-white/60">
                <strong className="text-[#36e4ff]">NEPTUN</strong> — єдиний сервіс з картою шахедів, траєкторіями,
                ШІ-аналізом та авіаційною картою. Ідеально для тих, хто хоче бачити повну картину загроз.
              </p>
            </div>
            <div className="bg-white/5 rounded-xl p-4">
              <h3 className="text-white font-medium mb-1">Для офіційних сповіщень</h3>
              <p className="text-sm text-white/60">
                <strong className="text-white/90">&ldquo;Повітряна тривога&rdquo;</strong> — офіційний додаток ДСНС. Рекомендуємо
                встановити як додатковий джерело, навіть якщо використовуєте NEPTUN.
              </p>
            </div>
            <div className="bg-white/5 rounded-xl p-4">
              <h3 className="text-white font-medium mb-1">Наша рекомендація</h3>
              <p className="text-sm text-white/60">
                Встановіть <strong className="text-[#36e4ff]">NEPTUN</strong> як основний інструмент моніторингу
                та <strong className="text-white/90">&ldquo;Повітряна тривога&rdquo;</strong> як офіційне резервне джерело.
                Два джерела — подвійна безпека.
              </p>
            </div>
          </div>

          <h2 className="text-xl font-semibold text-white mt-8">Підсумок</h2>
          <p>
            Кожен сервіс має свої переваги. NEPTUN виграє за функціоналом та швидкістю,
            &ldquo;Повітряна тривога&rdquo; — за офіційним статусом, alerts.in.ua — за простотою.
            Найголовніше — користуйтесь хоча б одним сервісом та не ігноруйте тривоги.
            Відкрийте <Link href="/" className="text-blue-400 hover:text-blue-300">карту NEPTUN</Link> прямо зараз.
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
