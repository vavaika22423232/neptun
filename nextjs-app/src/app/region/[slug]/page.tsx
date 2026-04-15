import type { Metadata } from 'next';
import Link from 'next/link';
import Footer from '@/components/Footer';
import { redisGetWithTimeout } from '@/lib/redis';
import type { Alarm } from '@/types';

// ISR: revalidate every 60 seconds for fresh alarm data
export const revalidate = 60;

interface RegionData {
  name: string;
  nameGen: string;
  city: string;
  population?: string;
  area?: string;
  neighbors?: string[];
}

const regionData: Record<string, RegionData> = {
  kyiv: { name: 'Київ', nameGen: 'Києва', city: 'Київ', population: '2,9 млн', area: '847 км²', neighbors: ['kyivska'] },
  kyivska: { name: 'Київська область', nameGen: 'Київської області', city: 'Київ', population: '1,8 млн', area: '28 131 км²', neighbors: ['kyiv', 'chernihivska', 'zhytomyrska', 'vinnytska', 'cherkaska', 'poltavska'] },
  kharkivska: { name: 'Харківська область', nameGen: 'Харківської області', city: 'Харків', population: '2,6 млн', area: '31 415 км²', neighbors: ['sumska', 'poltavska', 'dnipropetrovska', 'donetska', 'luhanska'] },
  odeska: { name: 'Одеська область', nameGen: 'Одеської області', city: 'Одеса', population: '2,4 млн', area: '33 310 км²', neighbors: ['mykolaivska', 'kirovohradska', 'vinnytska'] },
  dnipropetrovska: { name: 'Дніпропетровська область', nameGen: 'Дніпропетровської області', city: 'Дніпро', population: '3,1 млн', area: '31 914 км²', neighbors: ['poltavska', 'kharkivska', 'donetska', 'zaporizka', 'kirovohradska'] },
  zaporizka: { name: 'Запорізька область', nameGen: 'Запорізької області', city: 'Запоріжжя', population: '1,6 млн', area: '27 180 км²', neighbors: ['dnipropetrovska', 'donetska', 'khersonska'] },
  lvivska: { name: 'Львівська область', nameGen: 'Львівської області', city: 'Львів', population: '2,5 млн', area: '21 833 км²', neighbors: ['volynska', 'rivnenska', 'ternopilska', 'ivano-frankivska', 'zakarpatska'] },
  mykolaivska: { name: 'Миколаївська область', nameGen: 'Миколаївської області', city: 'Миколаїв', population: '1,1 млн', area: '24 585 км²', neighbors: ['odeska', 'kirovohradska', 'dnipropetrovska', 'khersonska'] },
  khersonska: { name: 'Херсонська область', nameGen: 'Херсонської області', city: 'Херсон', population: '1,0 млн', area: '28 461 км²', neighbors: ['mykolaivska', 'dnipropetrovska', 'zaporizka'] },
  poltavska: { name: 'Полтавська область', nameGen: 'Полтавської області', city: 'Полтава', population: '1,3 млн', area: '28 748 км²', neighbors: ['sumska', 'kharkivska', 'dnipropetrovska', 'kirovohradska', 'cherkaska', 'kyivska'] },
  vinnytska: { name: 'Вінницька область', nameGen: 'Вінницької області', city: 'Вінниця', population: '1,5 млн', area: '26 513 км²', neighbors: ['zhytomyrska', 'kyivska', 'cherkaska', 'kirovohradska', 'odeska', 'khmelnytska'] },
  cherkaska: { name: 'Черкаська область', nameGen: 'Черкаської області', city: 'Черкаси', population: '1,1 млн', area: '20 916 км²', neighbors: ['kyivska', 'poltavska', 'kirovohradska', 'vinnytska'] },
  zhytomyrska: { name: 'Житомирська область', nameGen: 'Житомирської області', city: 'Житомир', population: '1,2 млн', area: '29 832 км²', neighbors: ['kyivska', 'vinnytska', 'khmelnytska', 'rivnenska'] },
  sumska: { name: 'Сумська область', nameGen: 'Сумської області', city: 'Суми', population: '1,0 млн', area: '23 834 км²', neighbors: ['chernihivska', 'poltavska', 'kharkivska'] },
  chernihivska: { name: 'Чернігівська область', nameGen: 'Чернігівської області', city: 'Чернігів', population: '0,9 млн', area: '31 865 км²', neighbors: ['kyivska', 'sumska', 'poltavska'] },
  rivnenska: { name: 'Рівненська область', nameGen: 'Рівненської області', city: 'Рівне', population: '1,1 млн', area: '20 047 км²', neighbors: ['volynska', 'zhytomyrska', 'khmelnytska', 'ternopilska', 'lvivska'] },
  volynska: { name: 'Волинська область', nameGen: 'Волинської області', city: 'Луцьк', population: '1,0 млн', area: '20 143 км²', neighbors: ['rivnenska', 'lvivska'] },
  ternopilska: { name: 'Тернопільська область', nameGen: 'Тернопільської області', city: 'Тернопіль', population: '1,0 млн', area: '13 823 км²', neighbors: ['rivnenska', 'khmelnytska', 'ivano-frankivska', 'lvivska'] },
  'ivano-frankivska': { name: 'Івано-Франківська область', nameGen: 'Івано-Франківської області', city: 'Івано-Франківськ', population: '1,4 млн', area: '13 900 км²', neighbors: ['lvivska', 'ternopilska', 'chernivetska', 'zakarpatska'] },
  zakarpatska: { name: 'Закарпатська область', nameGen: 'Закарпатської області', city: 'Ужгород', population: '1,2 млн', area: '12 777 км²', neighbors: ['lvivska', 'ivano-frankivska'] },
  chernivetska: { name: 'Чернівецька область', nameGen: 'Чернівецької області', city: 'Чернівці', population: '0,9 млн', area: '8 097 км²', neighbors: ['ivano-frankivska', 'khmelnytska', 'vinnytska'] },
  khmelnytska: { name: 'Хмельницька область', nameGen: 'Хмельницької області', city: 'Хмельницький', population: '1,2 млн', area: '20 629 км²', neighbors: ['rivnenska', 'zhytomyrska', 'vinnytska', 'ternopilska', 'chernivetska'] },
  kirovohradska: { name: 'Кіровоградська область', nameGen: 'Кіровоградської області', city: 'Кропивницький', population: '0,9 млн', area: '24 588 км²', neighbors: ['cherkaska', 'poltavska', 'dnipropetrovska', 'mykolaivska', 'odeska', 'vinnytska'] },
  donetska: { name: 'Донецька область', nameGen: 'Донецької області', city: 'Донецьк', population: '4,1 млн', area: '26 517 км²', neighbors: ['kharkivska', 'dnipropetrovska', 'zaporizka', 'luhanska'] },
  luhanska: { name: 'Луганська область', nameGen: 'Луганської області', city: 'Луганськ', population: '2,1 млн', area: '26 684 км²', neighbors: ['kharkivska', 'donetska'] },
};

interface PageProps {
  params: Promise<{ slug: string }>;
}

// Fetch alarm status for a region directly from Redis (server-side)
async function getRegionAlarmStatus(regionName: string): Promise<{
  active: boolean;
  type: string | null;
  since: string | null;
  lastUpdated: string | null;
} | null> {
  try {
    const [alarms, lastUpdated] = await Promise.all([
      redisGetWithTimeout<Alarm[]>('alarms:all'),
      redisGetWithTimeout<string>('alarms:last_updated'),
    ]);
    if (!alarms || !Array.isArray(alarms)) return null;
    const match = alarms.find(
      (a) => a.regionName === regionName || a.regionId === regionName,
    );
    if (!match) return null;
    const isActive = match.activeAlerts && match.activeAlerts.length > 0;
    return {
      active: isActive,
      type: isActive ? (match.activeAlerts[0].type || 'Повітряна тривога') : null,
      since: isActive ? (match.activeAlerts[0].lastUpdate || null) : null,
      lastUpdated: lastUpdated || null,
    };
  } catch {
    return null;
  }
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params;
  const region = regionData[slug];
  const regionName = region?.name || slug;
  const regionGen = region?.nameGen || regionName;
  const regionCity = region?.city || regionName;

  const title = `Тривога ${regionName} зараз — карта тривог ${regionGen} онлайн | NEPTUN`;
  const description = `Повітряна тривога ${regionName} онлайн. Карта тривог ${regionGen} в реальному часі: шахеди, ракети, БПЛА. Тривога ${regionCity} зараз — дивіться на карті NEPTUN.`;

  return {
    title,
    description,
    keywords: `тривога ${regionCity}, тривога ${regionName}, карта тривог ${regionGen}, повітряна тривога ${regionCity}, шахеди ${regionCity}, ${regionCity} тривога зараз, карта тривог`,
    alternates: {
      canonical: `https://neptun.in.ua/region/${slug}`,
    },
    openGraph: {
      type: 'website',
      url: `https://neptun.in.ua/region/${slug}`,
      title: `Тривога ${regionName} — карта тривог NEPTUN`,
      description,
      siteName: 'NEPTUN Карта тривог',
      locale: 'uk_UA',
    },
    twitter: {
      card: 'summary_large_image',
      title: `Тривога ${regionName} — карта тривог NEPTUN`,
      description,
    },
  };
}

export async function generateStaticParams() {
  return Object.keys(regionData).map((slug) => ({ slug }));
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

export default async function RegionPage({ params }: PageProps) {
  const { slug } = await params;
  const region = regionData[slug];
  const regionName = region?.name || slug;
  const regionGen = region?.nameGen || regionName;
  const regionCity = region?.city || regionName;

  // Fetch live alarm status from Redis
  const alarmStatus = await getRegionAlarmStatus(regionName);

  // Get neighbor regions data
  const neighborSlugs = region?.neighbors || [];
  const neighborRegions = neighborSlugs
    .map((s) => ({ slug: s, ...regionData[s] }))
    .filter((n) => n.name);

  // JSON-LD structured data
  const jsonLdWebPage = {
    '@context': 'https://schema.org',
    '@type': 'WebPage',
    name: `Тривога ${regionName} зараз — карта тривог ${regionGen} онлайн`,
    url: `https://neptun.in.ua/region/${slug}`,
    description: `Повітряна тривога ${regionName} онлайн. Карта тривог ${regionGen} в реальному часі.`,
    isPartOf: { '@type': 'WebSite', name: 'NEPTUN', url: 'https://neptun.in.ua' },
    dateModified: new Date().toISOString(),
  };

  const jsonLdBreadcrumb = {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: [
      { '@type': 'ListItem', position: 1, name: 'Головна', item: 'https://neptun.in.ua' },
      { '@type': 'ListItem', position: 2, name: regionName, item: `https://neptun.in.ua/region/${slug}` },
    ],
  };

  const jsonLdPlace = {
    '@context': 'https://schema.org',
    '@type': 'Place',
    name: regionName,
    address: {
      '@type': 'PostalAddress',
      addressRegion: regionName,
      addressCountry: 'UA',
    },
  };

  return (
    <div className="min-h-screen bg-[var(--surface-dim)] text-white/80 p-6 max-w-3xl mx-auto">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLdWebPage) }} />
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLdBreadcrumb) }} />
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLdPlace) }} />

      <Link href="/" className="text-blue-400 hover:text-blue-300 text-sm mb-6 inline-block">
        &larr; Повернутися на карту
      </Link>

      <h1 className="text-3xl font-bold text-white mb-4">
        Тривога {regionName} зараз
      </h1>

      {/* Live alarm status banner */}
      {alarmStatus !== null && (
        <div
          className={`rounded-xl p-4 mb-6 flex items-center gap-3 ${
            alarmStatus.active
              ? 'bg-red-500/20 border border-red-500/40'
              : 'bg-green-500/15 border border-green-500/30'
          }`}
        >
          <span className={`text-2xl ${alarmStatus.active ? 'animate-pulse' : ''}`}>
            {alarmStatus.active ? '🔴' : '🟢'}
          </span>
          <div>
            <p className={`font-bold text-lg ${alarmStatus.active ? 'text-red-400' : 'text-green-400'}`}>
              {alarmStatus.active ? 'Повітряна тривога!' : 'Тривоги немає'}
            </p>
            {alarmStatus.active && alarmStatus.since && (
              <p className="text-white/50 text-sm">
                {alarmStatus.type || 'Повітряна тривога'} з {formatAlarmTime(alarmStatus.since)}
              </p>
            )}
            {alarmStatus.lastUpdated && (
              <p className="text-white/40 text-xs mt-0.5">
                Оновлено: {formatAlarmTime(alarmStatus.lastUpdated)}
              </p>
            )}
          </div>
        </div>
      )}

      <p className="text-lg mb-4">
        Актуальна карта тривог для {regionGen}. Дані оновлюються в реальному часі кожні 5 секунд.
        {region?.population && ` Населення регіону — ${region.population}.`}
      </p>

      <Link
        href="/"
        className="inline-flex items-center gap-2 bg-blue-500 hover:bg-blue-600 text-white px-6 py-3 rounded-xl font-medium transition-colors"
      >
        Відкрити карту тривог &rarr;
      </Link>

      {/* SEO-rich content */}
      <article className="mt-8 text-white/70 leading-relaxed space-y-4">
        <h2 className="text-xl font-semibold text-white/90">
          Карта тривог {regionGen} онлайн
        </h2>
        <p>
          Карта повітряних тривог {regionGen} відображає актуальну інформацію про повітряні тривоги,
          шахеди, ракети та БПЛА в реальному часі. Дивіться стан тривоги в{' '}
          {regionCity === regionName ? 'регіоні' : `місті ${regionCity}`} та навколишніх районах на
          інтерактивній карті NEPTUN.
        </p>
        <p>
          NEPTUN — найшвидша карта тривог України з оновленням кожні 5 секунд.
          Відстежуйте повітряні тривоги {regionGen} онлайн 24/7: push-сповіщення,
          траєкторія польоту шахедів та ракет, статус тривоги в усіх районах.
          {region?.area && ` Площа ${regionGen} — ${region.area}.`}
        </p>

        <h3 className="text-lg font-semibold text-white/80 mt-6">
          Що показує карта тривог {regionGen}?
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div className="bg-white/5 rounded-lg p-3">
            <p className="text-white/90 font-medium text-sm">🚨 Статус тривоги</p>
            <p className="text-xs text-white/50 mt-1">Активна тривога або відбій в {regionCity} та районах</p>
          </div>
          <div className="bg-white/5 rounded-lg p-3">
            <p className="text-white/90 font-medium text-sm">🛩️ Шахеди та БПЛА</p>
            <p className="text-xs text-white/50 mt-1">Напрямок та траєкторія польоту дронів</p>
          </div>
          <div className="bg-white/5 rounded-lg p-3">
            <p className="text-white/90 font-medium text-sm">🚀 Ракетна загроза</p>
            <p className="text-xs text-white/50 mt-1">Крилаті, балістичні ракети та КАБ</p>
          </div>
          <div className="bg-white/5 rounded-lg p-3">
            <p className="text-white/90 font-medium text-sm">⏱️ Хронологія</p>
            <p className="text-xs text-white/50 mt-1">Час оголошення та відбою тривоги</p>
          </div>
        </div>

        <h3 className="text-lg font-semibold text-white/80 mt-6">
          Як дізнатися про тривогу в {regionCity}?
        </h3>
        <ol className="list-decimal pl-6 space-y-2 text-sm">
          <li>
            <strong className="text-white/80">Відкрийте карту</strong> — перейдіть на{' '}
            <Link href="/" className="text-blue-400 hover:underline">neptun.in.ua</Link> або
            завантажте мобільний додаток
          </li>
          <li>
            <strong className="text-white/80">Знайдіть свій регіон</strong> — {regionName} на карті
            буде виділено червоним при тривозі
          </li>
          <li>
            <strong className="text-white/80">Увімкніть сповіщення</strong> — в додатку виберіть{' '}
            {regionCity} для push-повідомлень
          </li>
          <li>
            <strong className="text-white/80">Слідкуйте за загрозами</strong> — маркери шахедів та ракет
            оновлюються кожні 5 секунд
          </li>
        </ol>

        <h3 className="text-lg font-semibold text-white/80 mt-6">Мобільний додаток</h3>
        <p>
          Завантажте безкоштовний додаток NEPTUN та отримуйте push-сповіщення про тривоги в{' '}
          {regionCity} та {regionGen}:
        </p>
        <div className="flex flex-wrap gap-3 mt-2">
          <a
            href="https://play.google.com/store/apps/details?id=com.neptunalarm.neptun_alarm_app"
            className="inline-flex items-center gap-2 bg-green-500/15 text-green-400 px-4 py-2 rounded-lg text-sm hover:bg-green-500/25 transition-colors"
            rel="noopener"
          >
            Google Play
          </a>
          <a
            href="https://apps.apple.com/ua/app/neptun-карта-тривог/id6743640844"
            className="inline-flex items-center gap-2 bg-blue-500/15 text-blue-400 px-4 py-2 rounded-lg text-sm hover:bg-blue-500/25 transition-colors"
            rel="noopener"
          >
            App Store
          </a>
        </div>
      </article>

      {/* Neighboring regions */}
      {neighborRegions.length > 0 && (
        <div className="mt-8 space-y-3">
          <h2 className="text-lg font-semibold text-white/80">
            Сусідні регіони
          </h2>
          <p className="text-sm text-white/50">
            Стежте за тривогами в сусідніх областях — загрози часто переміщуються між регіонами
          </p>
          <div className="flex flex-wrap gap-2">
            {neighborRegions.map((n) => (
              <Link
                key={n.slug}
                href={`/region/${n.slug}`}
                className="px-3 py-1.5 rounded-lg text-xs bg-white/5 text-white/60 hover:bg-white/10 transition-colors"
              >
                {n.name}
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* All regions */}
      <div className="mt-8 space-y-3 text-sm text-white/50">
        <h2 className="text-lg font-semibold text-white/80">Усі регіони України</h2>
        <div className="flex flex-wrap gap-2">
          {Object.entries(regionData).map(([s, data]) => (
            <Link
              key={s}
              href={`/region/${s}`}
              className={`px-3 py-1.5 rounded-lg text-xs transition-colors ${
                s === slug
                  ? 'bg-blue-500/20 text-blue-400'
                  : 'bg-white/5 text-white/50 hover:bg-white/10'
              }`}
            >
              {data.name}
            </Link>
          ))}
        </div>
      </div>

      {/* Related pages */}
      <div className="mt-6 p-4 bg-white/5 rounded-xl text-sm">
        <h3 className="font-medium text-white mb-2">Корисні посилання</h3>
        <div className="flex flex-wrap gap-3 text-white/50">
          <Link href="/tryvoga-zaraz" className="text-blue-400 hover:underline">Тривога зараз</Link>
          <Link href="/povitryana-tryvoga" className="text-blue-400 hover:underline">Повітряна тривога</Link>
          <Link href="/karta-tryvoh" className="text-blue-400 hover:underline">Карта тривог</Link>
          <Link href="/karta-shahediv" className="text-blue-400 hover:underline">Карта шахедів</Link>
          <Link href="/radar-shahediv" className="text-blue-400 hover:underline">Радар шахедів</Link>
          <Link href="/faq" className="text-blue-400 hover:underline">FAQ</Link>
          <Link href="/about" className="text-blue-400 hover:underline">Про проєкт</Link>
        </div>
      </div>

      <Footer />
    </div>
  );
}
