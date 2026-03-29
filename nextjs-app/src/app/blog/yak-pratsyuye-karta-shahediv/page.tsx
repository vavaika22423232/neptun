import type { Metadata } from 'next';
import Link from 'next/link';
import Footer from '@/components/Footer';

export const metadata: Metadata = {
  title: 'Як працює карта шахедів NEPTUN — від Telegram до карти за 5 секунд | NEPTUN',
  description:
    'Технічний розбір: як NEPTUN збирає дані з Telegram-каналів ОВА, аналізує ШІ та відображає траєкторії шахедів на інтерактивній карті в реальному часі.',
  keywords:
    'як працює карта шахедів, NEPTUN технологія, відстеження шахедів, ШІ аналіз тривог, траєкторії дронів',
  alternates: { canonical: 'https://neptun.in.ua/blog/yak-pratsyuye-karta-shahediv' },
  openGraph: {
    type: 'article',
    url: 'https://neptun.in.ua/blog/yak-pratsyuye-karta-shahediv',
    title: 'Як працює карта шахедів NEPTUN',
    description: 'Від Telegram-повідомлення до відображення на карті за 5 секунд — технічний розбір.',
    images: [{ url: 'https://neptun.in.ua/api/og', width: 1200, height: 630 }],
    siteName: 'NEPTUN',
    locale: 'uk_UA',
  },
};

export default function Article() {
  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'BlogPosting',
    headline: 'Як працює карта шахедів NEPTUN — від Telegram до карти за 5 секунд',
    url: 'https://neptun.in.ua/blog/yak-pratsyuye-karta-shahediv',
    datePublished: '2025-02-10',
    dateModified: '2025-02-10',
    author: { '@type': 'Organization', name: 'NEPTUN', url: 'https://neptun.in.ua' },
    publisher: { '@type': 'Organization', name: 'NEPTUN', url: 'https://neptun.in.ua' },
    inLanguage: 'uk',
    mainEntityOfPage: 'https://neptun.in.ua/blog/yak-pratsyuye-karta-shahediv',
    breadcrumb: {
      '@type': 'BreadcrumbList',
      itemListElement: [
        { '@type': 'ListItem', position: 1, name: 'Головна', item: 'https://neptun.in.ua/' },
        { '@type': 'ListItem', position: 2, name: 'Блог', item: 'https://neptun.in.ua/blog' },
        { '@type': 'ListItem', position: 3, name: 'Як працює карта шахедів', item: 'https://neptun.in.ua/blog/yak-pratsyuye-karta-shahediv' },
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
        <span className="text-white/60">Як працює карта шахедів</span>
      </nav>

      <article>
        <div className="text-xs text-white/40 mb-3">
          <time dateTime="2025-02-10">10 лютого 2025</time> · 6 хв читання
        </div>

        <h1 className="text-3xl font-bold text-white mb-6">
          Як працює карта шахедів NEPTUN — від Telegram до карти за 5 секунд
        </h1>

        <div className="space-y-4 text-[15px] leading-relaxed">
          <p>
            Коли ви бачите на <Link href="/karta-shahediv" className="text-blue-400 hover:text-blue-300">карті шахедів NEPTUN</Link> траєкторію
            дрона, що рухається з Херсонщини на Миколаївщину — за цим стоїть складний технічний процес,
            який займає лише 5 секунд від появи повідомлення в Telegram до відображення на вашому екрані.
          </p>

          <h2 className="text-xl font-semibold text-white mt-8">Етап 1: Збір даних з Telegram</h2>
          <p>
            NEPTUN моніторить десятки офіційних Telegram-каналів у реальному часі. Це канали
            Обласних Військових Адміністрацій (ОВА) всіх 25 регіонів України, канал Повітряних сил ЗСУ
            та інші верифіковані джерела.
          </p>
          <p>
            Коли ОВА публікує повідомлення на кшталт &ldquo;Увага! Шахеди зі сходу, курс на захід.
            Миколаївська область&rdquo; — наш worker-процес миттєво отримує це повідомлення
            та передає його на обробку.
          </p>

          <h2 className="text-xl font-semibold text-white mt-8">Етап 2: ШІ-аналіз повідомлення</h2>
          <p>
            Кожне повідомлення проходить через модуль штучного інтелекту, який виконує кілька задач одночасно:
          </p>
          <ul className="list-disc pl-6 space-y-1.5">
            <li><strong className="text-white/90">Класифікація загрози</strong> — визначає тип: шахед, крилата ракета, балістична ракета, КАБ або розвідувальний БПЛА</li>
            <li><strong className="text-white/90">Виділення регіону</strong> — визначає, яка область згадується в повідомленні</li>
            <li><strong className="text-white/90">Геокодування</strong> — перетворює текстовий опис місцеположення (наприклад, &ldquo;на захід від Миколаєва&rdquo;) у географічні координати</li>
            <li><strong className="text-white/90">Визначення напрямку</strong> — аналізує курс руху загрози (північ, захід тощо)</li>
          </ul>

          <h2 className="text-xl font-semibold text-white mt-8">Етап 3: Побудова траєкторій</h2>
          <p>
            Це найцікавіша частина. Модуль траєкторного аналізу отримує послідовність повідомлень
            про один і той самий об&rsquo;єкт з різних регіонів і будує прогнозовану траєкторію руху.
          </p>
          <p>
            Наприклад, якщо шахед зафіксований спочатку в Херсонській, потім у Миколаївській,
            а потім в Одеській області — система будує вектор руху та прогнозує, куди він рухається далі.
            Це дозволяє користувачам заздалегідь отримати попередження.
          </p>

          <div className="bg-[#36e4ff]/5 border border-[#36e4ff]/10 rounded-xl p-4 my-4">
            <p className="text-[#36e4ff] text-sm">
              💡 Траєкторії на карті — це не точні координати GPS, а прогноз на основі послідовності повідомлень ОВА.
              Використовуйте їх як додатковий інструмент оцінки обстановки.
            </p>
          </div>

          <h2 className="text-xl font-semibold text-white mt-8">Етап 4: Оновлення карти в реальному часі</h2>
          <p>
            Оброблені дані надсилаються на сервер через Redis і миттєво транслюються всім підключеним
            користувачам через технологію SSE (Server-Sent Events). Це означає, що вам не потрібно
            оновлювати сторінку — карта оновлюється автоматично кожні 5 секунд.
          </p>
          <p>
            Для мобільного додатку одночасно надсилається push-сповіщення через Firebase Cloud Messaging,
            яке приходить навіть коли додаток закритий.
          </p>

          <h2 className="text-xl font-semibold text-white mt-8">Етап 5: Статус тривоги</h2>
          <p>
            Паралельно з відстеженням шахедів, NEPTUN отримує офіційний статус повітряної тривоги
            по всіх 25 областях через API ukrainealarm.com. Ці дані оновлюються кожні 10 секунд
            та відображаються на карті кольорами: червоний — тривога активна, зелений — відбій.
          </p>

          <h2 className="text-xl font-semibold text-white mt-8">Архітектура системи</h2>
          <div className="bg-white/5 rounded-xl p-5 font-mono text-sm text-white/70 space-y-1">
            <p>Telegram-канали ОВА</p>
            <p className="text-[#36e4ff]">&nbsp;&nbsp;↓ (миттєво)</p>
            <p>Python Worker — збір повідомлень</p>
            <p className="text-[#36e4ff]">&nbsp;&nbsp;↓ (ШІ-аналіз, ~1с)</p>
            <p>Класифікація + Геокодування + Траєкторії</p>
            <p className="text-[#36e4ff]">&nbsp;&nbsp;↓ (Redis pub/sub)</p>
            <p>Next.js сервер → SSE до браузера</p>
            <p className="text-[#36e4ff]">&nbsp;&nbsp;↓ (5 секунд)</p>
            <p>Карта на вашому екрані 🗺️</p>
          </div>

          <h2 className="text-xl font-semibold text-white mt-8">Надійність та масштабування</h2>
          <p>
            NEPTUN працює на кластері з 4 серверних процесів за nginx-балансувальником. Це забезпечує
            стабільну роботу навіть під час масованих атак, коли тисячі користувачів одночасно
            перевіряють карту. Середній uptime — 99.5%+.
          </p>

          <h2 className="text-xl font-semibold text-white mt-8">Підсумок</h2>
          <p>
            Карта шахедів NEPTUN — це не просто картинка. Це складна система збору, аналізу та
            візуалізації даних, яка працює 24/7 і допомагає мільйонам українців бути в курсі
            повітряної обстановки. Спробуйте{' '}
            <Link href="/" className="text-blue-400 hover:text-blue-300">карту тривог</Link> прямо зараз.
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
