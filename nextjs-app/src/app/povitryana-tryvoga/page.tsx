import type { Metadata } from 'next';
import Link from 'next/link';
import Footer from '@/components/Footer';

export const metadata: Metadata = {
  title: 'Повітряна тривога онлайн — карта що летить, мапа тривог України | NEPTUN',
  description:
    'Повітряна тривога онлайн: карта повітряних тривог і того, що летить (шахеди, ракети, БПЛА) в реальному часі по Україні. Мапа тривог, тривога зараз — NEPTUN 24/7.',
  keywords:
    'повітряна тривога, повітряна тривога онлайн, повітряна тривога онлайн карта що летить, повітряна тривога зараз, карта повітряних тривог, мапа тривог, тривога онлайн, мапа повітряних тривог, нептун карта',
  alternates: {
    canonical: 'https://neptun.in.ua/povitryana-tryvoga',
  },
  openGraph: {
    type: 'website',
    url: 'https://neptun.in.ua/povitryana-tryvoga',
    title: 'Повітряна тривога онлайн — карта повітряних тривог | NEPTUN',
    description: 'Повітряна тривога по всіх областях України в реальному часі. Карта повітряних тривог з шахедами та ракетами.',
    images: [{ url: 'https://neptun.in.ua/api/og', width: 1200, height: 630, alt: 'Повітряна тривога онлайн — NEPTUN' }],
    siteName: 'NEPTUN Карта тривог',
    locale: 'uk_UA',
  },
};

export default function PovitryanaTryvogaPage() {
  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'WebPage',
    name: 'Повітряна тривога онлайн — карта повітряних тривог України',
    url: 'https://neptun.in.ua/povitryana-tryvoga',
    description: 'Повітряна тривога онлайн в реальному часі. Карта повітряних тривог по всіх областях України.',
    isPartOf: { '@type': 'WebSite', name: 'NEPTUN', url: 'https://neptun.in.ua' },
    breadcrumb: {
      '@type': 'BreadcrumbList',
      itemListElement: [
        { '@type': 'ListItem', position: 1, name: 'Головна', item: 'https://neptun.in.ua' },
        { '@type': 'ListItem', position: 2, name: 'Повітряна тривога', item: 'https://neptun.in.ua/povitryana-tryvoga' },
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
        Повітряна тривога онлайн — карта повітряних тривог України
      </h1>

      <p className="text-lg text-white/70 mb-6">
        <strong className="text-white">Повітряна тривога онлайн</strong> по всіх 25 областях України — це не лише сирена по регіонах.
        NEPTUN показує <strong className="text-white">карту того, що летить</strong>: шахеди, ракети, КАБи та розвідувальні БПЛА з напрямком і траєкторіями.
        Якщо вам потрібна саме <strong className="text-white">онлайн карта «що летить»</strong> разом із тривогою — відкрийте інтерактивну мапу нижче.
      </p>

      <Link
        href="/"
        className="inline-flex items-center gap-2 bg-blue-500 hover:bg-blue-600 text-white px-6 py-3 rounded-xl font-medium transition-colors mb-8"
      >
        Відкрити карту повітряних тривог &rarr;
      </Link>

      <article className="text-white/70 leading-relaxed space-y-6">
        <section>
          <h2 className="text-xl font-semibold text-white/90 mb-3">Що таке повітряна тривога?</h2>
          <p>
            <strong className="text-white">Повітряна тривога</strong> — це сигнал цивільного захисту, який оголошується при загрозі
            ракетного удару, нальоту дронів або іншої повітряної атаки. Коли оголошується повітряна тривога, необхідно
            негайно перейти до найближчого укриття.
          </p>
          <p className="mt-3">
            <strong className="text-white">Карта повітряних тривог</strong> NEPTUN показує, в яких областях зараз активна тривога,
            а в яких оголошено відбій. Окрім статусу сирени, на карті відображаються реальні загрози:{' '}
            <Link href="/karta-shahediv" className="text-blue-400 hover:underline">шахеди</Link>, крилаті та балістичні ракети,
            розвідувальні БПЛА.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-white/90 mb-3">Повітряна тривога зараз — як дізнатися?</h2>
          <p>
            Щоб дізнатися, чи є <strong className="text-white">повітряна тривога зараз</strong> у вашому регіоні:
          </p>
          <ol className="list-decimal pl-6 space-y-2 mt-3">
            <li>Відкрийте <Link href="/" className="text-blue-400 hover:underline">neptun.in.ua</Link> — карта покаже всі активні тривоги</li>
            <li>Перейдіть на сторінку <Link href="/tryvoga-zaraz" className="text-blue-400 hover:underline">тривога зараз</Link> — зведення по всіх областях</li>
            <li>Виберіть свою область в розділі <Link href="/karta-tryvoh" className="text-blue-400 hover:underline">карта тривог по областях</Link></li>
            <li>Встановіть мобільний додаток NEPTUN для push-сповіщень</li>
          </ol>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-white/90 mb-3">Чому NEPTUN — найкраща карта повітряних тривог?</h2>
          <ul className="list-disc pl-6 space-y-2">
            <li><strong className="text-white">Не тільки тривоги</strong> — показуємо реальні загрози (шахеди, ракети) з траєкторіями</li>
            <li><strong className="text-white">Швидкість</strong> — дані з&apos;являються за 5-10 секунд після публікації в джерелі</li>
            <li><strong className="text-white">Всі області</strong> — 25 областей та місто Київ з деталізацією по районах</li>
            <li><strong className="text-white">Push-сповіщення</strong> — миттєві сповіщення про повітряну тривогу у вашому регіоні</li>
            <li><strong className="text-white">Безкоштовно</strong> — веб-версія та додаток без підписок</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-white/90 mb-3">Що робити під час повітряної тривоги?</h2>
          <p>
            При оголошенні повітряної тривоги негайно перейдіть до укриття. Якщо ви в будинку — спустіться в підвал або
            на нижній поверх, подалі від вікон. Детальні поради — у статті{' '}
            <Link href="/blog/shcho-robyty-pid-chas-tryvohy" className="text-blue-400 hover:underline">Що робити під час тривоги</Link>.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-white/90 mb-3">Завантажити додаток</h2>
          <p className="mb-3">
            Отримуйте push-сповіщення про повітряну тривогу у вашому регіоні:
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

        <section>
          <h2 className="text-xl font-semibold text-white/90 mb-3">Карта повітряних тривог по областях</h2>
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
        </section>

        <div className="p-4 bg-white/5 rounded-xl text-sm">
          <h3 className="font-medium text-white mb-2">Корисні посилання</h3>
          <div className="flex flex-wrap gap-3 text-white/50">
            <Link href="/tryvoga-zaraz" className="text-blue-400 hover:underline">Тривога зараз</Link>
            <Link href="/karta-tryvoh" className="text-blue-400 hover:underline">Карта тривог</Link>
            <Link href="/karta-shahediv" className="text-blue-400 hover:underline">Карта шахедів</Link>
            <Link href="/radar-shahediv" className="text-blue-400 hover:underline">Радар шахедів</Link>
            <Link href="/faq" className="text-blue-400 hover:underline">FAQ</Link>
          </div>
        </div>
      </article>

      <Footer />
    </div>
  );
}
