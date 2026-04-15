import type { Metadata } from 'next';
import Link from 'next/link';
import Footer from '@/components/Footer';
import { redisGetWithTimeout } from '@/lib/redis';
import type { Alarm } from '@/types';

// ISR: revalidate every 60 seconds for fresh alarm data
export const revalidate = 60;

interface RegionData {
  name: string;
  slug: string;
}

const REGIONS: RegionData[] = [
  { name: 'Київ', slug: 'kyiv' },
  { name: 'Київська область', slug: 'kyivska' },
  { name: 'Харківська область', slug: 'kharkivska' },
  { name: 'Одеська область', slug: 'odeska' },
  { name: 'Дніпропетровська область', slug: 'dnipropetrovska' },
  { name: 'Запорізька область', slug: 'zaporizka' },
  { name: 'Львівська область', slug: 'lvivska' },
  { name: 'Миколаївська область', slug: 'mykolaivska' },
  { name: 'Херсонська область', slug: 'khersonska' },
  { name: 'Полтавська область', slug: 'poltavska' },
  { name: 'Вінницька область', slug: 'vinnytska' },
  { name: 'Черкаська область', slug: 'cherkaska' },
  { name: 'Житомирська область', slug: 'zhytomyrska' },
  { name: 'Сумська область', slug: 'sumska' },
  { name: 'Чернігівська область', slug: 'chernihivska' },
  { name: 'Рівненська область', slug: 'rivnenska' },
  { name: 'Волинська область', slug: 'volynska' },
  { name: 'Тернопільська область', slug: 'ternopilska' },
  { name: 'Івано-Франківська область', slug: 'ivano-frankivska' },
  { name: 'Закарпатська область', slug: 'zakarpatska' },
  { name: 'Чернівецька область', slug: 'chernivetska' },
  { name: 'Хмельницька область', slug: 'khmelnytska' },
  { name: 'Кіровоградська область', slug: 'kirovohradska' },
  { name: 'Донецька область', slug: 'donetska' },
  { name: 'Луганська область', slug: 'luhanska' },
];

async function getAlarmsSummary(): Promise<{
  activeRegions: Set<string>;
  lastUpdated: string | null;
}> {
  try {
    const [alarms, lastUpdated] = await Promise.all([
      redisGetWithTimeout<Alarm[]>('alarms:all'),
      redisGetWithTimeout<string>('alarms:last_updated'),
    ]);
    const activeRegions = new Set<string>();
    if (alarms && Array.isArray(alarms)) {
      for (const a of alarms) {
        if (a.activeAlerts && a.activeAlerts.length > 0 && a.regionName) {
          activeRegions.add(a.regionName);
        }
      }
    }
    return { activeRegions, lastUpdated };
  } catch {
    return { activeRegions: new Set(), lastUpdated: null };
  }
}

function formatAlarmTime(isoString: string): string {
  try {
    const date = new Date(isoString);
    return date.toLocaleString('uk-UA', {
      timeZone: 'Europe/Kyiv',
      day: 'numeric',
      month: 'long',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return isoString;
  }
}

export const metadata: Metadata = {
  title: 'Тривога зараз — чи є тривога в Україні? Карта тривог онлайн | NEPTUN',
  description:
    'Тривога зараз — актуальний статус повітряних тривог по всіх областях України. Чи є тривога зараз? Дивіться зведення на NEPTUN. Карта тривог оновлюється кожні 5 секунд.',
  keywords:
    'тривога зараз, чи є тривога, де тривога, тривога в Україні, карта тривог зараз, повітряна тривога зараз, статус тривоги',
  alternates: {
    canonical: 'https://neptun.in.ua/tryvoga-zaraz',
  },
  openGraph: {
    type: 'website',
    url: 'https://neptun.in.ua/tryvoga-zaraz',
    title: 'Тривога зараз — карта тривог України | NEPTUN',
    description: 'Чи є тривога зараз? Актуальний статус повітряних тривог по всіх областях України.',
    images: [{ url: 'https://neptun.in.ua/api/og', width: 1200, height: 630, alt: 'Тривога зараз — NEPTUN' }],
    siteName: 'NEPTUN Карта тривог',
    locale: 'uk_UA',
  },
};

export default async function TryvogaZarazPage() {
  const { activeRegions, lastUpdated } = await getAlarmsSummary();
  const activeCount = activeRegions.size;

  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'WebPage',
    name: 'Тривога зараз — карта тривог України онлайн',
    url: 'https://neptun.in.ua/tryvoga-zaraz',
    description: 'Актуальний статус повітряних тривог по всіх областях України. Чи є тривога зараз?',
    isPartOf: { '@type': 'WebSite', name: 'NEPTUN', url: 'https://neptun.in.ua' },
    dateModified: new Date().toISOString(),
    breadcrumb: {
      '@type': 'BreadcrumbList',
      itemListElement: [
        { '@type': 'ListItem', position: 1, name: 'Головна', item: 'https://neptun.in.ua' },
        { '@type': 'ListItem', position: 2, name: 'Тривога зараз', item: 'https://neptun.in.ua/tryvoga-zaraz' },
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
        Тривога зараз — чи є тривога в Україні?
      </h1>

      {/* Live status banner */}
      <div
        className={`rounded-xl p-4 mb-6 flex items-center gap-3 ${
          activeCount > 0
            ? 'bg-red-500/20 border border-red-500/40'
            : 'bg-green-500/15 border border-green-500/30'
        }`}
      >
        <span className={`text-2xl ${activeCount > 0 ? 'animate-pulse' : ''}`}>
          {activeCount > 0 ? '🔴' : '🟢'}
        </span>
        <div>
          <p className={`font-bold text-lg ${activeCount > 0 ? 'text-red-400' : 'text-green-400'}`}>
            {activeCount > 0
              ? `Повітряна тривога! Активна в ${activeCount} ${activeCount === 1 ? 'області' : 'областях'}`
              : 'Тривоги немає'}
          </p>
          {lastUpdated && (
            <p className="text-white/50 text-sm">
              Оновлено: {formatAlarmTime(lastUpdated)}
            </p>
          )}
        </div>
      </div>

      <p className="text-lg text-white/70 mb-6">
        Актуальний статус повітряних тривог по всіх 25 областях України. Дані оновлюються в реальному часі кожні 5 секунд.
      </p>

      <Link
        href="/"
        className="inline-flex items-center gap-2 bg-blue-500 hover:bg-blue-600 text-white px-6 py-3 rounded-xl font-medium transition-colors mb-8"
      >
        Відкрити карту тривог &rarr;
      </Link>

      {/* Region status list */}
      <section className="mb-8">
        <h2 className="text-xl font-semibold text-white/90 mb-3">Тривога зараз по областях</h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          {REGIONS.map(({ name, slug }) => {
            const isActive = activeRegions.has(name);
            return (
              <Link
                key={slug}
                href={`/region/${slug}`}
                className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors ${
                  isActive
                    ? 'bg-red-500/15 border border-red-500/30 text-red-300'
                    : 'bg-white/5 border border-white/10 text-white/70 hover:bg-white/10'
                }`}
              >
                <span>{isActive ? '🔴' : '🟢'}</span>
                <span>{name}</span>
              </Link>
            );
          })}
        </div>
      </section>

      <article className="text-white/70 leading-relaxed space-y-6">
        <section>
          <h2 className="text-xl font-semibold text-white/90 mb-3">Як дізнатися, чи є тривога зараз?</h2>
          <p>
            <strong className="text-white">Тривога зараз</strong> — один з найпопулярніших запитів українців.
            NEPTUN показує актуальний статус повітряних тривог по всіх областях України. Сторінка оновлюється
            автоматично кожні 60 секунд, а інтерактивна карта на головній сторінці — кожні 5 секунд.
          </p>
          <p className="mt-3">
            Для миттєвих сповіщень про тривогу у вашому регіоні встановіть безкоштовний додаток NEPTUN
            для Android або iOS — ви отримаєте push-сповіщення навіть коли телефон заблоковано.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-white/90 mb-3">Корисні посилання</h2>
          <div className="flex flex-wrap gap-3 text-sm">
            <Link href="/" className="text-blue-400 hover:underline">Карта тривог</Link>
            <Link href="/povitryana-tryvoga" className="text-blue-400 hover:underline">Повітряна тривога</Link>
            <Link href="/karta-tryvoh" className="text-blue-400 hover:underline">Карта тривог по областях</Link>
            <Link href="/karta-shahediv" className="text-blue-400 hover:underline">Карта шахедів</Link>
            <Link href="/radar-shahediv" className="text-blue-400 hover:underline">Радар шахедів</Link>
            <Link href="/faq" className="text-blue-400 hover:underline">FAQ</Link>
          </div>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-white/90 mb-3">Завантажити додаток</h2>
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

      <Footer />
    </div>
  );
}
