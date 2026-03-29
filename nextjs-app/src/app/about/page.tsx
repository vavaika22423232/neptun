import type { Metadata } from 'next';
import Link from 'next/link';
import Footer from '@/components/Footer';

export const metadata: Metadata = {
  title: 'Про NEPTUN — Карта тривог та шахедів України в реальному часі',
  description:
    'NEPTUN — українська платформа моніторингу повітряних тривог, шахедів та ракетних загроз у реальному часі. Дізнайтесь про нашу місію, технології та команду.',
  alternates: {
    canonical: 'https://neptun.in.ua/about',
  },
  openGraph: {
    type: 'website',
    url: 'https://neptun.in.ua/about',
    title: 'Про NEPTUN — Карта тривог України',
    description: 'Українська платформа моніторингу повітряних тривог, шахедів та ракетних загроз.',
    images: [{ url: 'https://neptun.in.ua/api/og', width: 1200, height: 630, alt: 'Про NEPTUN' }],
    siteName: 'NEPTUN Карта тривог',
    locale: 'uk_UA',
  },
};

export default function AboutPage() {
  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'AboutPage',
    name: 'Про NEPTUN — Карта тривог України',
    url: 'https://neptun.in.ua/about',
    description: 'Українська платформа моніторингу повітряних тривог, шахедів та ракетних загроз у реальному часі.',
    isPartOf: { '@type': 'WebSite', name: 'NEPTUN', url: 'https://neptun.in.ua' },
    publisher: {
      '@type': 'Organization',
      name: 'NEPTUN',
      url: 'https://neptun.in.ua',
      logo: { '@type': 'ImageObject', url: 'https://neptun.in.ua/static/icons/icon-512.png', width: 512, height: 512 },
      foundingDate: '2024',
      description: 'Українська команда розробників, яка створює інструменти для безпеки громадян під час повітряних тривог.',
      sameAs: [
        'https://play.google.com/store/apps/details?id=com.neptunalarm.neptun_alarm_app',
        'https://apps.apple.com/ua/app/%D0%BA%D0%B0%D1%80%D1%82%D0%B0-%D1%82%D1%80%D0%B8%D0%B2%D0%BE%D0%B3-dron-alerts/id6758108122?l=uk',
      ],
    },
    breadcrumb: {
      '@type': 'BreadcrumbList',
      itemListElement: [
        { '@type': 'ListItem', position: 1, name: 'Головна', item: 'https://neptun.in.ua/' },
        { '@type': 'ListItem', position: 2, name: 'Про нас', item: 'https://neptun.in.ua/about' },
      ],
    },
  };

  return (
    <div className="min-h-screen bg-[var(--surface-dim)] text-white/80 p-6 max-w-3xl mx-auto">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />

      <Link href="/" className="text-blue-400 hover:text-blue-300 text-sm mb-6 inline-block">
        &larr; Повернутися на карту
      </Link>

      <h1 className="text-3xl font-bold text-white mb-6">Про NEPTUN — карта тривог та шахедів України</h1>

      <div className="space-y-4 text-[15px] leading-relaxed">
        <p>
          <strong className="text-white">NEPTUN</strong> — це українська платформа моніторингу повітряних
          тривог та загроз в реальному часі, створена для безпеки громадян України. Проєкт працює цілодобово
          24/7, збираючи, аналізуючи та візуалізуючи інформацію про повітряні тривоги, рух шахедів, ракет
          та інших загроз на інтерактивній карті.
        </p>

        <h2 className="text-xl font-semibold text-white mt-8">Наша місія</h2>
        <p>
          Місія NEPTUN — надати кожному громадянину України швидкий та зручний доступ до інформації
          про повітряні загрози. Ми прагнемо, щоб люди могли вчасно реагувати на тривоги та приймати
          обґрунтовані рішення щодо своєї безпеки. NEPTUN створений українською командою розробників,
          яка щодня працює над покращенням точності та швидкості сервісу.
        </p>

        <h2 className="text-xl font-semibold text-white mt-8">Як працює NEPTUN</h2>
        <p>
          Система NEPTUN автоматично збирає інформацію з офіційних Telegram-каналів Обласних Військових
          Адміністрацій (ОВА), Повітряних сил ЗСУ та інших відкритих джерел. Повідомлення обробляються за
          допомогою штучного інтелекту (ШІ), який класифікує тип загрози — шахеди, крилаті ракети, балістичні
          ракети, КАБ або розвідувальні БПЛА — та визначає напрямок руху.
        </p>
        <p>
          Результати аналізу відображаються на інтерактивній карті з оновленням кожні 5 секунд. Користувачі
          бачать активні повітряні тривоги по всіх 25 областях, траєкторії руху шахедів та ракет, а також
          прогнозований напрямок загроз.
        </p>

        <h2 className="text-xl font-semibold text-white mt-8">Технології</h2>
        <ul className="list-disc pl-6 space-y-2">
          <li><strong className="text-white/90">ШІ-аналіз повідомлень</strong> — автоматична класифікація типу загрози, виділення ключової інформації з текстових повідомлень</li>
          <li><strong className="text-white/90">Моніторинг у реальному часі</strong> — SSE (Server-Sent Events) для миттєвої доставки оновлень без затримок</li>
          <li><strong className="text-white/90">Траєкторний аналіз</strong> — прогнозування напрямку руху БПЛА на основі послідовних повідомлень з різних областей</li>
          <li><strong className="text-white/90">Push-сповіщення</strong> — миттєві push-повідомлення через Firebase Cloud Messaging для Android та iOS</li>
          <li><strong className="text-white/90">Геокодування</strong> — визначення точного місцеположення загроз за текстовими описами з повідомлень ОВА</li>
        </ul>

        <h2 className="text-xl font-semibold text-white mt-8">Можливості платформи</h2>
        <div className="grid sm:grid-cols-2 gap-4">
          <div className="bg-white/5 rounded-xl p-4">
            <h3 className="text-white font-medium mb-2">Карта тривог</h3>
            <p className="text-sm text-white/60">Повітряні тривоги по всіх 25 областях та районах України — офіційний статус в реальному часі</p>
          </div>
          <div className="bg-white/5 rounded-xl p-4">
            <h3 className="text-white font-medium mb-2">Радар шахедів</h3>
            <p className="text-sm text-white/60">Відстеження БПЛА Shahed-136/131 з траєкторіями польоту, напрямком та швидкістю на карті</p>
          </div>
          <div className="bg-white/5 rounded-xl p-4">
            <h3 className="text-white font-medium mb-2">Мобільний додаток</h3>
            <p className="text-sm text-white/60">Безкоштовний додаток для Android та iOS з push-сповіщеннями про тривоги у вашому регіоні</p>
          </div>
          <div className="bg-white/5 rounded-xl p-4">
            <h3 className="text-white font-medium mb-2">Авіаційна карта</h3>
            <p className="text-sm text-white/60">Моніторинг повітряного простору — цивільні та військові повітряні судна, зони обмежень NOTAM</p>
          </div>
        </div>

        <h2 className="text-xl font-semibold text-white mt-8">Чому обирають NEPTUN</h2>
        <ul className="list-disc pl-6 space-y-2">
          <li>Оновлення кожні 5 секунд — одна з найшвидших карт тривог в Україні</li>
          <li>Охоплення всіх 25 областей з детальною інформацією по районах</li>
          <li>Безкоштовний доступ — веб-версія та мобільні додатки без підписок</li>
          <li>Інтуїтивний інтерфейс з темною темою для комфортного використання вночі</li>
          <li>Мультиплатформність — працює у браузері, на Android та iOS</li>
          <li>Конфіденційність — не збираємо персональні дані користувачів</li>
        </ul>

        <h2 className="text-xl font-semibold text-white mt-8">Завантажити додаток</h2>
        <div className="flex flex-wrap gap-4 mt-2">
          <a
            href="https://play.google.com/store/apps/details?id=com.neptunalarm.neptun_alarm_app"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 px-4 py-2.5 bg-white/10 hover:bg-white/15 rounded-xl text-white transition-colors"
          >
            <span className="text-xl">▶</span> Google Play
          </a>
          <a
            href="https://apps.apple.com/ua/app/%D0%BA%D0%B0%D1%80%D1%82%D0%B0-%D1%82%D1%80%D0%B8%D0%B2%D0%BE%D0%B3-dron-alerts/id6758108122?l=uk"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 px-4 py-2.5 bg-white/10 hover:bg-white/15 rounded-xl text-white transition-colors"
          >
            <span className="text-xl">🍎</span> App Store
          </a>
        </div>

        <h2 className="text-xl font-semibold text-white mt-8">Важливо</h2>
        <p>
          NEPTUN <strong className="text-white">не є офіційною</strong> системою оповіщення Міністерства
          оборони чи ДСНС. Для отримання офіційних повідомлень про тривоги використовуйте державні ресурси
          та додаток &ldquo;Повітряна тривога&rdquo;. NEPTUN є додатковим інструментом, який допомагає
          візуалізувати обстановку та приймати обґрунтовані рішення щодо власної безпеки.
        </p>

        <h2 className="text-xl font-semibold text-white mt-8">Корисні посилання</h2>
        <div className="flex flex-wrap gap-3 mb-6">
          <Link href="/" className="text-blue-400 hover:underline">Карта тривог</Link>
          <Link href="/povitryana-tryvoga" className="text-blue-400 hover:underline">Повітряна тривога</Link>
          <Link href="/tryvoga-zaraz" className="text-blue-400 hover:underline">Тривога зараз</Link>
          <Link href="/karta-tryvoh" className="text-blue-400 hover:underline">Карта тривог по областях</Link>
          <Link href="/karta-shahediv" className="text-blue-400 hover:underline">Карта шахедів</Link>
          <Link href="/faq" className="text-blue-400 hover:underline">FAQ</Link>
        </div>

        <h2 className="text-xl font-semibold text-white mt-8">Зворотний зв&apos;язок</h2>
        <p>
          Маєте пропозиції, знайшли помилку або хочете допомогти проєкту? Напишіть нам у{' '}
          <a href="https://t.me/+aBR79kExNQM1ZjZi" target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:text-blue-300">
            Telegram
          </a>{' '}
          або на сторінці <Link href="/contact" className="text-blue-400 hover:text-blue-300">контактів</Link>.
        </p>
      </div>

      <Footer />
    </div>
  );
}
