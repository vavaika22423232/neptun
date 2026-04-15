import type { Metadata } from 'next';
import Link from 'next/link';
import Footer from '@/components/Footer';
import { redisGetWithTimeout } from '@/lib/redis';
import type { Alarm } from '@/types';

export const revalidate = 60;

interface CityData {
  name: string;
  nameGen: string;
  regionSlug: string;
  regionName: string;
  population: string;
  description: string;
  landmarks: string[];
  shelterTips: string[];
}

const cityData: Record<string, CityData> = {
  'kharkiv': {
    name: 'Харків',
    nameGen: 'Харкова',
    regionSlug: 'kharkivska',
    regionName: 'Харківська область',
    population: '1,4 млн',
    description: 'Харків — друге за населенням місто України, розташоване за 40 км від кордону з Росією. З лютого 2022 року є одним з найбільш обстрілюваних міст. Мешканці стикаються з ракетними ударами, КАБ та шахедами практично щодня. Час підльоту балістичних ракет — менше 3 хвилин.',
    landmarks: ['Площа Свободи', 'Станція метро Держпром', 'ХНУ імені Каразіна', 'Парк Горького'],
    shelterTips: ['Метро Харкова — надійне укриття (3 лінії, 30 станцій)', 'Час підльоту КАБ та балістики мінімальний — перебувайте поблизу укриттів', 'Підвали багатоповерхівок — основне укриття у житлових районах'],
  },
  'odesa': {
    name: 'Одеса',
    nameGen: 'Одеси',
    regionSlug: 'odeska',
    regionName: 'Одеська область',
    population: '1,0 млн',
    description: 'Одеса — портове місто на Чорному морі, стратегічно важливе для експорту зернових. Зазнає регулярних ударів крилатими ракетами (Калібр) та шахедами, переважно в нічний час. Атаки спрямовані на портову інфраструктуру та енергетичні об\'єкти.',
    landmarks: ['Потьомкінські сходи', 'Дерибасівська вулиця', 'Одеський порт', 'Оперний театр'],
    shelterTips: ['Катакомби Одеси — унікальні природні укриття', 'Підвали історичних будівель у центрі добре захищені', 'Слідкуйте за повідомленнями ОК «Південь» в Telegram'],
  },
  'dnipro': {
    name: 'Дніпро',
    nameGen: 'Дніпра',
    regionSlug: 'dnipropetrovska',
    regionName: 'Дніпропетровська область',
    population: '0,9 млн',
    description: 'Дніпро — великий промисловий центр у центральній Україні. Місто зазнає регулярних ракетних ударів, зокрема балістичними ракетами Іскандер. Один з найтрагічніших ударів стався по житловому будинку 14 січня 2023 року.',
    landmarks: ['Набережна Дніпра', 'Проспект Яворницького', 'Монастирський острів', 'ДНУ імені Гончара'],
    shelterTips: ['Метро Дніпра (6 станцій) — надійне укриття', 'Час підльоту балістичних ракет ~5 хвилин', 'Промислові підвали та бомбосховища добре обладнані'],
  },
  'lviv': {
    name: 'Львів',
    nameGen: 'Львова',
    regionSlug: 'lvivska',
    regionName: 'Львівська область',
    population: '0,7 млн',
    description: 'Львів — культурна столиця України, місто-притулок для внутрішніх переселенців. Хоча розташоване на заході, зазнає ударів крилатими ракетами Х-101, запущеними з Каспійського моря та стратегічних бомбардувальників. Атаки спрямовані переважно на енергетичну інфраструктуру.',
    landmarks: ['Площа Ринок', 'Оперний театр', 'Високий Замок', 'Личаківський цвинтар'],
    shelterTips: ['Підвали старого міста — стіни завтовшки 1-2 метри, надійний захист', 'Тривоги зазвичай тривають 20-40 хвилин', 'Більшість атак — крилаті ракети з часом підльоту 40-60 хв'],
  },
  'zaporizhzhia': {
    name: 'Запоріжжя',
    nameGen: 'Запоріжжя',
    regionSlug: 'zaporizka',
    regionName: 'Запорізька область',
    population: '0,7 млн',
    description: 'Запоріжжя — прифронтове місто, яке зазнає постійних обстрілів. Розташоване на березі Дніпра, є промисловим центром із стратегічними підприємствами. Поблизу розташована Запорізька АЕС — найбільша атомна електростанція в Європі.',
    landmarks: ['Острів Хортиця', 'ДніпроГЕС', 'Проспект Соборний', 'Запорізький дуб'],
    shelterTips: ['Прифронтове місто — постійно тримайте тривожну валізу готовою', 'Балістичні ракети та КАБ — основні загрози', 'Слідкуйте за повідомленнями ОВА Запорізької області'],
  },
  'mykolaiv': {
    name: 'Миколаїв',
    nameGen: 'Миколаєва',
    regionSlug: 'mykolaivska',
    regionName: 'Миколаївська область',
    population: '0,5 млн',
    description: 'Миколаїв — портове місто, яке з перших днів повномасштабного вторгнення було на лінії фронту. У 2022 році зазнавало щоденних обстрілів. Зараз місто періодично атакують ракетами та шахедами. Відоме суднобудівною промисловістю.',
    landmarks: ['Суднобудівний завод', 'Набережна річки Інгул', 'Миколаївський зоопарк', 'Біблійний сад'],
    shelterTips: ['Місто часто на шляху шахедів з Чорного моря', 'Підвали та бомбосховища — основний тип укриттів', 'Нічні атаки шахедами — найчастіший сценарій'],
  },
  'kyiv-city': {
    name: 'Київ',
    nameGen: 'Києва',
    regionSlug: 'kyiv',
    regionName: 'Київ',
    population: '2,9 млн',
    description: 'Київ — столиця України, одне з основних міст-цілей для ракетних ударів. З осені 2022 року зазнає масованих ракетних та дронових атак на енергетичну інфраструктуру. Потужна система ППО захищає місто, але загроза залишається постійною.',
    landmarks: ['Софія Київська', 'Києво-Печерська Лавра', 'Майдан Незалежності', 'Хрещатик'],
    shelterTips: ['Метро Києва (3 лінії, 52 станції) — найкраще укриття', 'Середній час тривоги — 45 хвилин', 'Потужна ППО, але не ігноруйте тривоги — уламки також небезпечні'],
  },
  'vinnytsia': {
    name: 'Вінниця',
    nameGen: 'Вінниці',
    regionSlug: 'vinnytska',
    regionName: 'Вінницька область',
    population: '0,4 млн',
    description: 'Вінниця — обласний центр у центральній Україні. 14 липня 2022 року місто зазнало трагічного ракетного удару по центру міста (офісний центр «Юпітер»), який забрав 27 життів. Місто продовжує зазнавати ракетних та дронових атак.',
    landmarks: ['Фонтан Roshen', 'Вежа водонапірна', 'Муріїнський монастир', 'Парк Горького'],
    shelterTips: ['Типова загроза — крилаті ракети Х-101 з часом підльоту ~50 хвилин', 'Підвали державних установ обладнані як укриття', 'Слідкуйте за повідомленнями Вінницької ОВА'],
  },
  'sumy': {
    name: 'Суми',
    nameGen: 'Сум',
    regionSlug: 'sumska',
    regionName: 'Сумська область',
    population: '0,3 млн',
    description: 'Суми — обласний центр на північному сході України, розташований за 50 км від кордону з Росією. Місто зазнає регулярних обстрілів КАБ, ракетами та артилерією. Одне з найбільш небезпечних міст через близькість до кордону.',
    landmarks: ['Альтанки на Незалежності', 'Сумський обласний театр', 'Парк Асмолова'],
    shelterTips: ['Близькість до кордону — мінімальний час реагування', 'КАБ та артилерія — основні загрози міста', 'Тримайте тривожну валізу завжди під рукою'],
  },
  'poltava': {
    name: 'Полтава',
    nameGen: 'Полтави',
    regionSlug: 'poltavska',
    regionName: 'Полтавська область',
    population: '0,3 млн',
    description: 'Полтава — історичне місто в центральній Україні. 3 вересня 2024 року місто зазнало одного з найбільших ударів — балістичною ракетою по навчальному закладу. Полтава регулярно опиняється на шляху шахедів, що летять з південного сходу.',
    landmarks: ['Білі бесідки', 'Полтавська битва (1709)', 'Успенський собор', 'Хрестовоздвиженський монастир'],
    shelterTips: ['Балістичні ракети — найбільша загроза через мінімальний час підльоту', 'Місто на перетині маршрутів шахедів', 'Підвали старих будівель — основні укриття'],
  },
};

const allCitySlugs = Object.keys(cityData);

interface PageProps {
  params: Promise<{ slug: string }>;
}

async function getRegionAlarmStatus(regionName: string): Promise<{
  active: boolean;
  type: string | null;
  since: string | null;
} | null> {
  try {
    const alarms = await redisGetWithTimeout<Alarm[]>('alarms:all');
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
    };
  } catch {
    return null;
  }
}

export async function generateStaticParams() {
  return allCitySlugs.map((slug) => ({ slug }));
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params;
  const city = cityData[slug];
  if (!city) return { title: 'Місто не знайдено' };

  const title = `Повітряна тривога ${city.name} зараз — карта тривог онлайн | NEPTUN`;
  const description = `Повітряна тривога в ${city.nameGen} зараз — онлайн карта тривог. Статус тривоги, шахеди, ракети, укриття — ${city.name} на карті NEPTUN.`;

  return {
    title,
    description,
    keywords: `тривога ${city.name}, повітряна тривога ${city.name}, карта тривог ${city.name}, ${city.name} зараз, шахеди ${city.name}, укриття ${city.name}`,
    alternates: { canonical: `https://neptun.in.ua/city/${slug}` },
    openGraph: {
      type: 'website',
      url: `https://neptun.in.ua/city/${slug}`,
      title: `Тривога ${city.name} зараз — NEPTUN`,
      description,
      images: [{ url: 'https://neptun.in.ua/api/og', width: 1200, height: 630, alt: `Тривога ${city.name}` }],
      siteName: 'NEPTUN Карта тривог',
      locale: 'uk_UA',
    },
  };
}

export default async function CityPage({ params }: PageProps) {
  const { slug } = await params;
  const city = cityData[slug];

  if (!city) {
    return (
      <div className="min-h-screen bg-[var(--surface-dim)] text-white p-6 flex items-center justify-center">
        <div className="text-center">
          <h1 className="text-2xl font-bold mb-4">Місто не знайдено</h1>
          <Link href="/" className="text-blue-400 hover:text-blue-300">Повернутися на карту</Link>
        </div>
      </div>
    );
  }

  const alarmStatus = await getRegionAlarmStatus(city.regionName);

  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'WebPage',
    name: `Повітряна тривога ${city.name} — NEPTUN`,
    url: `https://neptun.in.ua/city/${slug}`,
    description: `Карта тривог ${city.nameGen} онлайн. Статус тривоги, шахеди, ракети в реальному часі.`,
    isPartOf: { '@type': 'WebSite', name: 'NEPTUN', url: 'https://neptun.in.ua' },
    breadcrumb: {
      '@type': 'BreadcrumbList',
      itemListElement: [
        { '@type': 'ListItem', position: 1, name: 'Головна', item: 'https://neptun.in.ua/' },
        { '@type': 'ListItem', position: 2, name: city.regionName, item: `https://neptun.in.ua/region/${city.regionSlug}` },
        { '@type': 'ListItem', position: 3, name: city.name, item: `https://neptun.in.ua/city/${slug}` },
      ],
    },
  };

  return (
    <div className="min-h-screen bg-[var(--surface-dim)] text-white/80 p-6 max-w-3xl mx-auto">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />

      <nav className="text-sm text-white/40 mb-6 flex items-center gap-2 flex-wrap">
        <Link href="/" className="text-blue-400 hover:text-blue-300">Карта</Link>
        <span>/</span>
        <Link href={`/region/${city.regionSlug}`} className="text-blue-400 hover:text-blue-300">{city.regionName}</Link>
        <span>/</span>
        <span className="text-white/60">{city.name}</span>
      </nav>

      <h1 className="text-3xl font-bold text-white mb-4">
        Повітряна тривога {city.name} зараз — карта тривог онлайн
      </h1>

      {/* Live alarm banner */}
      {alarmStatus && (
        <div className={`rounded-xl p-4 mb-6 border ${
          alarmStatus.active
            ? 'bg-red-500/10 border-red-500/30'
            : 'bg-green-500/10 border-green-500/30'
        }`}>
          <div className="flex items-center gap-3">
            <span className={`text-2xl ${alarmStatus.active ? 'animate-pulse' : ''}`}>
              {alarmStatus.active ? '🔴' : '🟢'}
            </span>
            <div>
              <div className={`font-semibold ${alarmStatus.active ? 'text-red-400' : 'text-green-400'}`}>
                {alarmStatus.active
                  ? `🚨 ТРИВОГА в ${city.nameGen}!`
                  : `Відбій тривоги — ${city.name} у безпеці`}
              </div>
              {alarmStatus.active && alarmStatus.type && (
                <div className="text-sm text-white/50 mt-0.5">
                  Тип: {alarmStatus.type}
                  {alarmStatus.since && ` · з ${new Date(alarmStatus.since).toLocaleTimeString('uk-UA', { hour: '2-digit', minute: '2-digit' })}`}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      <div className="space-y-6 text-[15px] leading-relaxed">
        {/* City info */}
        <section>
          <div className="grid grid-cols-2 gap-3 mb-4">
            <div className="bg-white/5 rounded-xl p-4 text-center">
              <div className="text-xl font-bold text-[#36e4ff]">{city.population}</div>
              <div className="text-xs text-white/40">Населення</div>
            </div>
            <div className="bg-white/5 rounded-xl p-4 text-center">
              <div className="text-xl font-bold text-[#36e4ff]">{city.regionName}</div>
              <div className="text-xs text-white/40">Область</div>
            </div>
          </div>
          <p>{city.description}</p>
        </section>

        {/* CTA */}
        <div className="bg-[#36e4ff]/5 border border-[#36e4ff]/10 rounded-xl p-5 text-center">
          <h2 className="text-lg font-semibold text-white mb-2">
            Відстежуйте тривоги {city.nameGen} в реальному часі
          </h2>
          <p className="text-sm text-white/60 mb-4">
            Карта NEPTUN показує тривоги, рух шахедів та ракет з оновленням кожні 5 секунд.
          </p>
          <Link
            href="/"
            className="inline-block px-6 py-2.5 bg-[#36e4ff]/20 hover:bg-[#36e4ff]/30 border border-[#36e4ff]/20 rounded-xl text-[#36e4ff] font-medium transition-colors"
          >
            Відкрити карту тривог
          </Link>
        </div>

        {/* Shelter tips */}
        <section>
          <h2 className="text-xl font-semibold text-white mb-3">
            Укриття та безпека в {city.nameGen}
          </h2>
          <ul className="space-y-2">
            {city.shelterTips.map((tip, i) => (
              <li key={i} className="flex items-start gap-2">
                <span className="text-[#5ef5c4] mt-0.5">•</span>
                <span>{tip}</span>
              </li>
            ))}
          </ul>
          <p className="mt-3 text-sm text-white/50">
            Детальну інструкцію дій під час тривоги читайте у статті{' '}
            <Link href="/blog/shcho-robyty-pid-chas-tryvohy" className="text-blue-400 hover:text-blue-300">
              «Що робити під час повітряної тривоги»
            </Link>.
          </p>
        </section>

        {/* Landmarks */}
        <section>
          <h2 className="text-xl font-semibold text-white mb-3">
            {city.name} — ключові об&rsquo;єкти
          </h2>
          <div className="flex flex-wrap gap-2">
            {city.landmarks.map((l) => (
              <span key={l} className="px-3 py-1.5 bg-white/5 border border-white/5 rounded-lg text-sm text-white/60">
                {l}
              </span>
            ))}
          </div>
        </section>

        {/* App download */}
        <section>
          <h2 className="text-xl font-semibold text-white mb-3">
            Push-сповіщення про тривоги в {city.nameGen}
          </h2>
          <p className="mb-3">
            Завантажте додаток NEPTUN та отримуйте push-сповіщення про тривоги у вашому місті:
          </p>
          <div className="flex flex-wrap gap-3">
            <a
              href="https://play.google.com/store/apps/details?id=com.neptunalarm.neptun_alarm_app"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-4 py-2.5 bg-white/10 hover:bg-white/15 rounded-xl text-white text-sm transition-colors no-underline"
            >
              ▶ Google Play
            </a>
            <a
              href="https://apps.apple.com/ua/app/%D0%BA%D0%B0%D1%80%D1%82%D0%B0-%D1%82%D1%80%D0%B8%D0%B2%D0%BE%D0%B3-dron-alerts/id6758108122?l=uk"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 px-4 py-2.5 bg-white/10 hover:bg-white/15 rounded-xl text-white text-sm transition-colors no-underline"
            >
              🍎 App Store
            </a>
          </div>
        </section>

        {/* Related links */}
        <section>
          <h2 className="text-xl font-semibold text-white mb-3">Корисні посилання</h2>
          <nav className="flex flex-wrap gap-2">
            <Link href={`/region/${city.regionSlug}`} className="px-3 py-1.5 bg-[#36e4ff]/5 hover:bg-[#36e4ff]/10 border border-[#36e4ff]/8 rounded-lg text-sm text-[#36e4ff]/70 hover:text-[#36e4ff] no-underline transition-colors">
              Тривоги {city.regionName}
            </Link>
            <Link href="/karta-tryvoh" className="px-3 py-1.5 bg-[#36e4ff]/5 hover:bg-[#36e4ff]/10 border border-[#36e4ff]/8 rounded-lg text-sm text-[#36e4ff]/70 hover:text-[#36e4ff] no-underline transition-colors">
              Карта тривог
            </Link>
            <Link href="/karta-shahediv" className="px-3 py-1.5 bg-[#36e4ff]/5 hover:bg-[#36e4ff]/10 border border-[#36e4ff]/8 rounded-lg text-sm text-[#36e4ff]/70 hover:text-[#36e4ff] no-underline transition-colors">
              Карта шахедів
            </Link>
            <Link href="/statistics" className="px-3 py-1.5 bg-[#36e4ff]/5 hover:bg-[#36e4ff]/10 border border-[#36e4ff]/8 rounded-lg text-sm text-[#36e4ff]/70 hover:text-[#36e4ff] no-underline transition-colors">
              Статистика тривог
            </Link>
            <Link href="/blog" className="px-3 py-1.5 bg-[#36e4ff]/5 hover:bg-[#36e4ff]/10 border border-[#36e4ff]/8 rounded-lg text-sm text-[#36e4ff]/70 hover:text-[#36e4ff] no-underline transition-colors">
              Блог
            </Link>
          </nav>
        </section>
      </div>

      <Footer />
    </div>
  );
}
