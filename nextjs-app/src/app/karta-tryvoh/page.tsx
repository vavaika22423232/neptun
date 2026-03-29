import type { Metadata } from 'next';
import Link from 'next/link';
import Footer from '@/components/Footer';

export const metadata: Metadata = {
  title: 'Карта тривог і мапа тривог України онлайн — повітряна тривога | NEPTUN',
  description:
    'Карта тривог та мапа тривог України онлайн. Повітряна тривога по областях у реальному часі, шахеди, ракети, БПЛА. Карта повітряних тривог з push 24/7.',
  keywords:
    'карта тривог, карта тревог, мапа тривог, мапа тревог, карта повітряних тривог, повітряна тривога карта, тривога онлайн, карта тривог України, карта тревог Украины',
  alternates: {
    canonical: 'https://neptun.in.ua/karta-tryvoh',
  },
  openGraph: {
    type: 'website',
    url: 'https://neptun.in.ua/karta-tryvoh',
    title: 'Карта тривог України онлайн — NEPTUN',
    description: 'Повітряна тривога по всіх областях України в реальному часі. Шахеди, ракети, БПЛА на інтерактивній мапі тривог.',
    images: [{ url: 'https://neptun.in.ua/api/og', width: 1200, height: 630, alt: 'Карта тривог України онлайн — NEPTUN' }],
    siteName: 'NEPTUN Карта тривог',
    locale: 'uk_UA',
  },
};

export default function KartaTryvohPage() {
  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'WebPage',
    name: 'Карта тривог України онлайн — NEPTUN',
    url: 'https://neptun.in.ua/karta-tryvoh',
    description: 'Інтерактивна карта повітряних тривог по всіх областях України в реальному часі.',
    isPartOf: { '@type': 'WebSite', name: 'NEPTUN', url: 'https://neptun.in.ua' },
    breadcrumb: {
      '@type': 'BreadcrumbList',
      itemListElement: [
        { '@type': 'ListItem', position: 1, name: 'Головна', item: 'https://neptun.in.ua' },
        { '@type': 'ListItem', position: 2, name: 'Карта тривог', item: 'https://neptun.in.ua/karta-tryvoh' },
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
        Карта тривог України онлайн — повітряна тривога в реальному часі
      </h1>

      <p className="text-lg text-white/70 mb-6">
        Інтерактивна карта повітряних тривог по всіх 25 областях України. Дивіться стан тривоги у вашому
        регіоні, відстежуйте загрози та отримуйте push-сповіщення — все безкоштовно на NEPTUN.
      </p>

      <Link
        href="/"
        className="inline-flex items-center gap-2 bg-blue-500 hover:bg-blue-600 text-white px-6 py-3 rounded-xl font-medium transition-colors mb-8"
      >
        Відкрити карту тривог &rarr;
      </Link>

      <article className="text-white/70 leading-relaxed space-y-6">
        <section>
          <h2 className="text-xl font-semibold text-white/90 mb-3">Що таке карта тривог?</h2>
          <p>
            <strong className="text-white">Карта тривог</strong> (також «мапа тривог», «карта повітряних тривог») — це інтерактивна
            онлайн-карта України, яка відображає актуальний статус повітряної тривоги по всіх регіонах. Коли оголошується тривога,
            відповідна область на карті підсвічується червоним кольором. Коли лунає відбій — колір змінюється на зелений.
          </p>
          <p className="mt-3">
            NEPTUN — це не просто <strong className="text-white">карта тривог</strong>. Окрім статусу тривоги, на карті відображаються
            реальні повітряні загрози: <Link href="/karta-shahediv" className="text-blue-400 hover:underline">шахеди</Link>,
            крилаті та балістичні ракети, КАБи, розвідувальні
            <Link href="/radar-shahediv" className="text-blue-400 hover:underline"> БПЛА</Link>.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-white/90 mb-3">Що показує карта тривог NEPTUN?</h2>
          <div className="space-y-3">
            <div className="flex items-start gap-3 bg-white/5 rounded-xl p-4">
              <span className="text-2xl">🔴</span>
              <div>
                <h3 className="font-medium text-white">Повітряна тривога</h3>
                <p className="text-sm">Активні сирени по всіх областях та районах України. Час оголошення та тривалість тривоги.</p>
              </div>
            </div>
            <div className="flex items-start gap-3 bg-white/5 rounded-xl p-4">
              <span className="text-2xl">🟠</span>
              <div>
                <h3 className="font-medium text-white">Шахеди та БПЛА</h3>
                <p className="text-sm">Реальний рух дронів-камікадзе та розвідувальних БПЛА з траєкторіями та напрямком.</p>
              </div>
            </div>
            <div className="flex items-start gap-3 bg-white/5 rounded-xl p-4">
              <span className="text-2xl">🔵</span>
              <div>
                <h3 className="font-medium text-white">Крилаті ракети</h3>
                <p className="text-sm">Х-101, Калібр та інші крилаті ракети з позначками місцезнаходження та курсу.</p>
              </div>
            </div>
            <div className="flex items-start gap-3 bg-white/5 rounded-xl p-4">
              <span className="text-2xl">⚡</span>
              <div>
                <h3 className="font-medium text-white">Балістична загроза</h3>
                <p className="text-sm">Балістичні ракети (Іскандер, Кинжал). Відображаються миттєво з банером термінового оповіщення.</p>
              </div>
            </div>
          </div>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-white/90 mb-3">Чим NEPTUN кращий за інші карти тривог?</h2>
          <ul className="list-disc pl-6 space-y-2">
            <li><strong className="text-white">Не тільки тривоги</strong> — ми показуємо реальні загрози (шахеди, ракети), а не лише статус сирени</li>
            <li><strong className="text-white">Швидкість</strong> — інформація з&apos;являється на карті за 5-10 секунд після публікації</li>
            <li><strong className="text-white">Траєкторії</strong> — бачите не тільки де загроза, а й куди вона рухається</li>
            <li><strong className="text-white">Push-сповіщення</strong> — миттєві сповіщення про тривогу у вашому регіоні (мобільний додаток)</li>
            <li><strong className="text-white">Безкоштовно</strong> — без підписок, реклами та обмежень</li>
            <li><strong className="text-white">Мобільний додаток</strong> — доступний для Android та iOS</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-white/90 mb-3">Як користуватися картою тривог?</h2>
          <ol className="list-decimal pl-6 space-y-2">
            <li>Відкрийте <Link href="/" className="text-blue-400 hover:underline">neptun.in.ua</Link> в браузері або встановіть додаток</li>
            <li>Карта відобразить всі активні тривоги та загрози автоматично</li>
            <li>Натисніть на будь-який маркер, щоб побачити деталі: тип загрози, кількість, напрямок</li>
            <li>Використовуйте кнопки зуму для наближення до вашого регіону</li>
            <li>Встановіть додаток для отримання push-сповіщень</li>
          </ol>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-white/90 mb-3">Джерела даних</h2>
          <p>
            Карта тривог NEPTUN збирає дані з офіційних Telegram-каналів обласних військових адміністрацій (ОВА)
            та перевірених моніторингових груп. Усі повідомлення автоматично аналізуються за допомогою ШІ
            для визначення типу загрози, місцезнаходження та напрямку руху.
          </p>
          <p className="mt-2 text-sm text-white/50">
            <strong className="text-white/70">Важливо:</strong> NEPTUN не є офіційною системою оповіщення.
            Для офіційної інформації використовуйте державний додаток «Повітряна тривога».
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-white/90 mb-3">Завантажити додаток</h2>
          <p className="mb-3">
            Отримуйте push-сповіщення про тривоги та рух шахедів у вашому регіоні:
          </p>
          <div className="flex flex-wrap gap-3">
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
      </article>

      {/* Related pages */}
      <div className="mt-6 p-4 bg-white/5 rounded-xl text-sm">
        <h3 className="font-medium text-white mb-2">Корисні посилання</h3>
        <div className="flex flex-wrap gap-3 text-white/50">
          <Link href="/tryvoga-zaraz" className="text-blue-400 hover:underline">Тривога зараз</Link>
          <Link href="/povitryana-tryvoga" className="text-blue-400 hover:underline">Повітряна тривога</Link>
          <Link href="/karta-shahediv" className="text-blue-400 hover:underline">Карта шахедів</Link>
          <Link href="/radar-shahediv" className="text-blue-400 hover:underline">Радар шахедів</Link>
          <Link href="/faq" className="text-blue-400 hover:underline">FAQ</Link>
          <Link href="/about" className="text-blue-400 hover:underline">Про проєкт</Link>
        </div>
      </div>

      {/* Region links */}
      <div className="mt-8 text-sm">
        <h2 className="text-lg font-semibold text-white/80 mb-3">Карта тривог по областях</h2>
        <div className="flex flex-wrap gap-2">
          {[
            { slug: 'kyiv', name: 'Київ' },
            { slug: 'kharkivska', name: 'Харківська' },
            { slug: 'odeska', name: 'Одеська' },
            { slug: 'dnipropetrovska', name: 'Дніпропетровська' },
            { slug: 'zaporizka', name: 'Запорізька' },
            { slug: 'lvivska', name: 'Львівська' },
            { slug: 'mykolaivska', name: 'Миколаївська' },
            { slug: 'khersonska', name: 'Херсонська' },
            { slug: 'poltavska', name: 'Полтавська' },
            { slug: 'vinnytska', name: 'Вінницька' },
            { slug: 'sumska', name: 'Сумська' },
            { slug: 'chernihivska', name: 'Чернігівська' },
            { slug: 'zhytomyrska', name: 'Житомирська' },
            { slug: 'cherkaska', name: 'Черкаська' },
            { slug: 'rivnenska', name: 'Рівненська' },
            { slug: 'volynska', name: 'Волинська' },
            { slug: 'ternopilska', name: 'Тернопільська' },
            { slug: 'ivano-frankivska', name: 'Івано-Франківська' },
            { slug: 'zakarpatska', name: 'Закарпатська' },
            { slug: 'chernivetska', name: 'Чернівецька' },
            { slug: 'khmelnytska', name: 'Хмельницька' },
            { slug: 'kirovohradska', name: 'Кіровоградська' },
            { slug: 'donetska', name: 'Донецька' },
            { slug: 'luhanska', name: 'Луганська' },
          ].map(({ slug, name }) => (
            <Link
              key={slug}
              href={`/region/${slug}`}
              className="px-3 py-1.5 rounded-lg text-xs bg-white/5 text-white/50 hover:bg-white/10 transition-colors"
            >
              {name}
            </Link>
          ))}
        </div>
      </div>

      <Footer />
    </div>
  );
}
