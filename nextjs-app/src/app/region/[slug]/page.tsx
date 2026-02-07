import type { Metadata } from 'next';
import Link from 'next/link';

interface RegionData {
  name: string;
  nameGen: string;
  city: string;
}

const regionData: Record<string, RegionData> = {
  kyiv: { name: 'Київ', nameGen: 'Києва', city: 'Київ' },
  kyivska: { name: 'Київська область', nameGen: 'Київської області', city: 'Київ' },
  kharkivska: { name: 'Харківська область', nameGen: 'Харківської області', city: 'Харків' },
  odeska: { name: 'Одеська область', nameGen: 'Одеської області', city: 'Одеса' },
  dnipropetrovska: { name: 'Дніпропетровська область', nameGen: 'Дніпропетровської області', city: 'Дніпро' },
  zaporizka: { name: 'Запорізька область', nameGen: 'Запорізької області', city: 'Запоріжжя' },
  lvivska: { name: 'Львівська область', nameGen: 'Львівської області', city: 'Львів' },
  mykolaivska: { name: 'Миколаївська область', nameGen: 'Миколаївської області', city: 'Миколаїв' },
  khersonska: { name: 'Херсонська область', nameGen: 'Херсонської області', city: 'Херсон' },
  poltavska: { name: 'Полтавська область', nameGen: 'Полтавської області', city: 'Полтава' },
  vinnytska: { name: 'Вінницька область', nameGen: 'Вінницької області', city: 'Вінниця' },
  cherkaska: { name: 'Черкаська область', nameGen: 'Черкаської області', city: 'Черкаси' },
  zhytomyrska: { name: 'Житомирська область', nameGen: 'Житомирської області', city: 'Житомир' },
  sumska: { name: 'Сумська область', nameGen: 'Сумської області', city: 'Суми' },
  chernihivska: { name: 'Чернігівська область', nameGen: 'Чернігівської області', city: 'Чернігів' },
  rivnenska: { name: 'Рівненська область', nameGen: 'Рівненської області', city: 'Рівне' },
  volynska: { name: 'Волинська область', nameGen: 'Волинської області', city: 'Луцьк' },
  ternopilska: { name: 'Тернопільська область', nameGen: 'Тернопільської області', city: 'Тернопіль' },
  'ivano-frankivska': { name: 'Івано-Франківська область', nameGen: 'Івано-Франківської області', city: 'Івано-Франківськ' },
  zakarpatska: { name: 'Закарпатська область', nameGen: 'Закарпатської області', city: 'Ужгород' },
  chernivetska: { name: 'Чернівецька область', nameGen: 'Чернівецької області', city: 'Чернівці' },
  khmelnytska: { name: 'Хмельницька область', nameGen: 'Хмельницької області', city: 'Хмельницький' },
  kirovohradska: { name: 'Кіровоградська область', nameGen: 'Кіровоградської області', city: 'Кропивницький' },
  donetska: { name: 'Донецька область', nameGen: 'Донецької області', city: 'Донецьк' },
  luhanska: { name: 'Луганська область', nameGen: 'Луганської області', city: 'Луганськ' },
};

interface PageProps {
  params: Promise<{ slug: string }>;
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
      images: [{ url: 'https://neptun.in.ua/static/og-image.png', width: 1200, height: 630 }],
      siteName: 'NEPTUN Карта тривог',
      locale: 'uk_UA',
    },
    twitter: {
      card: 'summary_large_image',
      title: `Тривога ${regionName} — карта тривог NEPTUN`,
      description,
      images: ['https://neptun.in.ua/static/og-image.png'],
    },
  };
}

export async function generateStaticParams() {
  return Object.keys(regionData).map((slug) => ({ slug }));
}

export default async function RegionPage({ params }: PageProps) {
  const { slug } = await params;
  const region = regionData[slug];
  const regionName = region?.name || slug;
  const regionGen = region?.nameGen || regionName;
  const regionCity = region?.city || regionName;

  // JSON-LD structured data for this region
  const jsonLdWebPage = {
    '@context': 'https://schema.org',
    '@type': 'WebPage',
    name: `Тривога ${regionName} зараз — карта тривог ${regionGen} онлайн`,
    url: `https://neptun.in.ua/region/${slug}`,
    description: `Повітряна тривога ${regionName} онлайн. Карта тривог ${regionGen} в реальному часі.`,
    isPartOf: { '@type': 'WebSite', name: 'NEPTUN', url: 'https://neptun.in.ua' },
  };

  const jsonLdBreadcrumb = {
    '@context': 'https://schema.org',
    '@type': 'BreadcrumbList',
    itemListElement: [
      { '@type': 'ListItem', position: 1, name: 'Головна', item: 'https://neptun.in.ua' },
      { '@type': 'ListItem', position: 2, name: 'Карта тривог', item: 'https://neptun.in.ua/#map' },
      { '@type': 'ListItem', position: 3, name: regionName, item: `https://neptun.in.ua/region/${slug}` },
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
    <div className="min-h-screen bg-[#0a0e17] text-white/80 p-6 max-w-3xl mx-auto">
      {/* JSON-LD */}
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLdWebPage) }} />
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLdBreadcrumb) }} />
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLdPlace) }} />

      <Link href="/" className="text-blue-400 hover:text-blue-300 text-sm mb-6 inline-block">
        &larr; Повернутися на карту
      </Link>

      <h1 className="text-3xl font-bold text-white mb-4">
        Тривога {regionName} зараз
      </h1>

      <p className="text-lg mb-4">
        Актуальна карта тривог для {regionGen}. Дані оновлюються в реальному часі.
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
          Карта повітряних тривог {regionGen} відображає актуальну інформацію про повітряні тривоги, шахеди, ракети та БПЛА в реальному часі.
          Дивіться стан тривоги в {regionCity === regionName ? 'регіоні' : `місті ${regionCity}`} та навколишніх районах на інтерактивній карті NEPTUN.
        </p>
        <p>
          NEPTUN — найшвидша карта тривог України. Відстежуйте повітряні тривоги {regionGen} онлайн 24/7.
          Оновлення кожні 5 секунд, push-сповіщення, траєкторія польоту шахедів та ракет.
        </p>

        <h3 className="text-lg font-semibold text-white/80 mt-6">Що показує карта тривог {regionGen}?</h3>
        <ul className="list-disc pl-6 space-y-1">
          <li>Активна повітряна тривога в {regionCity} та районах {regionGen}</li>
          <li>Шахеди та БПЛА — напрямок польоту, траєкторія</li>
          <li>Ракетна загроза — крилаті та балістичні ракети</li>
          <li>Час оголошення та відбою тривоги</li>
        </ul>

        <h3 className="text-lg font-semibold text-white/80 mt-6">Мобільний додаток</h3>
        <p>
          Завантажте безкоштовний{' '}
          <a
            href="https://play.google.com/store/apps/details?id=com.neptunalarm.neptun_alarm_app"
            className="text-green-400 hover:underline"
            rel="noopener"
          >
            додаток NEPTUN з Google Play
          </a>{' '}
          та отримуйте push-сповіщення про тривоги в {regionCity} та {regionGen}.
        </p>
      </article>

      {/* Other regions */}
      <div className="mt-8 space-y-3 text-sm text-white/50">
        <h2 className="text-lg font-semibold text-white/80">Інші регіони</h2>
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
    </div>
  );
}
