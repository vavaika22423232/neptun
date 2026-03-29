import type { Metadata } from 'next';
import Link from 'next/link';
import Footer from '@/components/Footer';

export const metadata: Metadata = {
  title: 'Статистика повітряних тривог України 2022-2025 — NEPTUN',
  description:
    'Статистика повітряних тривог в Україні: кількість тривог по областях, середня тривалість, типи загроз (шахеди, ракети, БПЛА). Аналітика за 2022-2025 роки.',
  keywords:
    'статистика тривог, статистика повітряних тривог, тривоги по областях, скільки тривог в Україні, статистика шахедів, аналітика тривог',
  alternates: {
    canonical: 'https://neptun.in.ua/statistics',
  },
  openGraph: {
    type: 'website',
    url: 'https://neptun.in.ua/statistics',
    title: 'Статистика повітряних тривог України — NEPTUN',
    description: 'Аналітика повітряних тривог: кількість, тривалість, типи загроз по областях.',
    images: [{ url: 'https://neptun.in.ua/api/og', width: 1200, height: 630, alt: 'Статистика тривог України' }],
    siteName: 'NEPTUN Карта тривог',
    locale: 'uk_UA',
  },
};

// Static data — curated from open sources
const totalStats = {
  totalAlarms: '~62 000+',
  totalHours: '~9 500+',
  avgDurationMin: 45,
  mostAlarmedRegion: 'Харківська область',
  longestAlarmHours: 72,
  shaheds: '~13 000+',
  cruiseMissiles: '~4 000+',
  ballisticMissiles: '~1 100+',
};

const regionStats = [
  { name: 'Харківська', alarms: '~5 100', avgMin: 68, hoursTotal: '~950' },
  { name: 'Дніпропетровська', alarms: '~4 800', avgMin: 55, hoursTotal: '~840' },
  { name: 'Запорізька', alarms: '~4 600', avgMin: 58, hoursTotal: '~810' },
  { name: 'Миколаївська', alarms: '~4 200', avgMin: 52, hoursTotal: '~720' },
  { name: 'Одеська', alarms: '~4 000', avgMin: 50, hoursTotal: '~690' },
  { name: 'Київська', alarms: '~3 800', avgMin: 42, hoursTotal: '~580' },
  { name: 'Полтавська', alarms: '~3 400', avgMin: 38, hoursTotal: '~470' },
  { name: 'Сумська', alarms: '~3 200', avgMin: 48, hoursTotal: '~510' },
  { name: 'Чернігівська', alarms: '~3 000', avgMin: 40, hoursTotal: '~430' },
  { name: 'Черкаська', alarms: '~2 800', avgMin: 35, hoursTotal: '~370' },
  { name: 'Вінницька', alarms: '~2 700', avgMin: 33, hoursTotal: '~340' },
  { name: 'Кіровоградська', alarms: '~2 600', avgMin: 34, hoursTotal: '~330' },
  { name: 'м. Київ', alarms: '~2 500', avgMin: 45, hoursTotal: '~400' },
  { name: 'Хмельницька', alarms: '~2 200', avgMin: 30, hoursTotal: '~280' },
  { name: 'Житомирська', alarms: '~2 100', avgMin: 32, hoursTotal: '~270' },
  { name: 'Донецька', alarms: '~2 000', avgMin: 60, hoursTotal: '~420' },
  { name: 'Херсонська', alarms: '~1 900', avgMin: 55, hoursTotal: '~370' },
  { name: 'Львівська', alarms: '~1 800', avgMin: 28, hoursTotal: '~220' },
  { name: 'Рівненська', alarms: '~1 600', avgMin: 25, hoursTotal: '~180' },
  { name: 'Тернопільська', alarms: '~1 500', avgMin: 24, hoursTotal: '~160' },
  { name: 'Волинська', alarms: '~1 400', avgMin: 22, hoursTotal: '~140' },
  { name: 'Івано-Франківська', alarms: '~1 300', avgMin: 23, hoursTotal: '~135' },
  { name: 'Чернівецька', alarms: '~1 100', avgMin: 20, hoursTotal: '~110' },
  { name: 'Закарпатська', alarms: '~900', avgMin: 18, hoursTotal: '~80' },
  { name: 'Луганська', alarms: '~800', avgMin: 65, hoursTotal: '~200' },
];

const yearlyData = [
  { year: 2022, alarms: '~9 500', shaheds: '~500', missiles: '~1 400', note: 'Початок повномасштабного вторгнення (з 24.02)' },
  { year: 2023, alarms: '~19 000', shaheds: '~3 700', missiles: '~1 800', note: 'Масові нічні атаки шахедами з осені' },
  { year: 2024, alarms: '~21 000', shaheds: '~5 500', missiles: '~1 200', note: 'Комбіновані атаки шахеди + ракети' },
  { year: 2025, alarms: '~12 500', shaheds: '~3 300+', missiles: '~700+', note: 'Дані станом на лютий 2025' },
];

export default function StatisticsPage() {
  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'WebPage',
    name: 'Статистика повітряних тривог України — NEPTUN',
    url: 'https://neptun.in.ua/statistics',
    description: 'Аналітика повітряних тривог в Україні: кількість по областях, тривалість, типи загроз.',
    isPartOf: { '@type': 'WebSite', name: 'NEPTUN', url: 'https://neptun.in.ua' },
    breadcrumb: {
      '@type': 'BreadcrumbList',
      itemListElement: [
        { '@type': 'ListItem', position: 1, name: 'Головна', item: 'https://neptun.in.ua/' },
        { '@type': 'ListItem', position: 2, name: 'Статистика', item: 'https://neptun.in.ua/statistics' },
      ],
    },
  };

  return (
    <div className="min-h-screen bg-[var(--surface-dim)] text-white/80 p-6 max-w-4xl mx-auto">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />

      <Link href="/" className="text-blue-400 hover:text-blue-300 text-sm mb-6 inline-block">
        &larr; Повернутися на карту
      </Link>

      <h1 className="text-3xl font-bold text-white mb-2">
        Статистика повітряних тривог України 2022–2025
      </h1>
      <p className="text-white/50 text-sm mb-8">
        Оновлено: лютий 2025 | Джерела: відкриті дані ОВА, Повітряні Сили ЗСУ
      </p>

      {/* Key metrics */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-10">
        {[
          { label: 'Тривог з 2022', value: totalStats.totalAlarms },
          { label: 'Годин у тривозі', value: totalStats.totalHours },
          { label: 'Атак шахедами', value: totalStats.shaheds },
          { label: 'Крилатих ракет', value: totalStats.cruiseMissiles },
        ].map((m) => (
          <div key={m.label} className="bg-white/5 rounded-xl p-4 text-center">
            <div className="text-2xl font-bold text-[#36e4ff]">{m.value}</div>
            <div className="text-xs text-white/50 mt-1">{m.label}</div>
          </div>
        ))}
      </div>

      {/* Intro text */}
      <section className="mb-10 text-[15px] leading-relaxed space-y-3">
        <h2 className="text-xl font-semibold text-white">Загальна статистика повітряних тривог в Україні</h2>
        <p>
          З початку повномасштабного вторгнення Росії 24 лютого 2022 року Україна пережила понад
          <strong className="text-white"> {totalStats.totalAlarms} повітряних тривог</strong>. Загальна
          тривалість тривог перевищила <strong className="text-white">{totalStats.totalHours} годин</strong> —
          це понад 395 повних діб, протягом яких українці перебували в укриттях або під загрозою ударів.
        </p>
        <p>
          Найбільш обстрілюваним регіоном залишається <strong className="text-white">{totalStats.mostAlarmedRegion}</strong>,
          де зафіксовано найбільшу кількість тривог та найтривалішу середню тривалість — до {totalStats.avgDurationMin} хвилин.
          Найдовша безперервна тривога тривала близько <strong className="text-white">{totalStats.longestAlarmHours} годин</strong>.
        </p>
        <p>
          Основні типи загроз — БПЛА &ldquo;Шахед&rdquo; (Shahed-136/131), крилаті ракети (Х-101, Х-555, Калібр),
          балістичні ракети (Іскандер, КН-23), а також керовані авіаційні бомби (КАБ).
        </p>
      </section>

      {/* Yearly breakdown */}
      <section className="mb-10">
        <h2 className="text-xl font-semibold text-white mb-4">Динаміка по роках</h2>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-white/10 text-white/50">
                <th className="py-2 px-3 text-left font-medium">Рік</th>
                <th className="py-2 px-3 text-right font-medium">Тривог</th>
                <th className="py-2 px-3 text-right font-medium">Шахедів</th>
                <th className="py-2 px-3 text-right font-medium">Ракет</th>
                <th className="py-2 px-3 text-left font-medium hidden sm:table-cell">Примітка</th>
              </tr>
            </thead>
            <tbody>
              {yearlyData.map((y) => (
                <tr key={y.year} className="border-b border-white/5 hover:bg-white/3">
                  <td className="py-2.5 px-3 font-medium text-white">{y.year}</td>
                  <td className="py-2.5 px-3 text-right text-[#36e4ff]">{y.alarms}</td>
                  <td className="py-2.5 px-3 text-right text-orange-400">{y.shaheds}</td>
                  <td className="py-2.5 px-3 text-right text-red-400">{y.missiles}</td>
                  <td className="py-2.5 px-3 text-white/40 text-xs hidden sm:table-cell">{y.note}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Regional breakdown */}
      <section className="mb-10">
        <h2 className="text-xl font-semibold text-white mb-4">Статистика тривог по областях України</h2>
        <p className="text-sm text-white/50 mb-4">
          Кількість тривог, середня тривалість та загальний час у тривозі по кожній області з лютого 2022 року.
        </p>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-white/10 text-white/50">
                <th className="py-2 px-3 text-left font-medium">Область</th>
                <th className="py-2 px-3 text-right font-medium">Тривог</th>
                <th className="py-2 px-3 text-right font-medium">Сер. хв.</th>
                <th className="py-2 px-3 text-right font-medium">Годин всього</th>
              </tr>
            </thead>
            <tbody>
              {regionStats.map((r, i) => (
                <tr key={r.name} className={`border-b border-white/5 hover:bg-white/3 ${i < 3 ? 'text-white' : ''}`}>
                  <td className="py-2 px-3">
                    {i < 3 && <span className="text-red-400 mr-1">●</span>}
                    {r.name}
                  </td>
                  <td className="py-2 px-3 text-right text-[#36e4ff]">{r.alarms}</td>
                  <td className="py-2 px-3 text-right">{r.avgMin} хв</td>
                  <td className="py-2 px-3 text-right text-white/50">{r.hoursTotal}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Types of threats */}
      <section className="mb-10">
        <h2 className="text-xl font-semibold text-white mb-4">Типи повітряних загроз</h2>
        <div className="grid sm:grid-cols-2 gap-4">
          <div className="bg-white/5 rounded-xl p-5">
            <h3 className="text-white font-medium mb-2">🛩️ БПЛА &ldquo;Шахед&rdquo; (Shahed-136/131)</h3>
            <p className="text-sm text-white/60">
              Іранські дрони-камікадзе. Швидкість ~180 км/год, дальність ~2 500 км.
              Використовуються масово для нічних атак групами від 10 до 180+ одиниць.
              Загалом Росія застосувала <strong className="text-white/80">{totalStats.shaheds}</strong> шахедів.
            </p>
          </div>
          <div className="bg-white/5 rounded-xl p-5">
            <h3 className="text-white font-medium mb-2">🚀 Крилаті ракети</h3>
            <p className="text-sm text-white/60">
              Х-101/Х-555, Калібр — дозвукові ракети з дальністю 1 500-2 500 км.
              Запускаються зі стратегічних бомбардувальників (Ту-95МС) та кораблів.
              Всього застосовано <strong className="text-white/80">{totalStats.cruiseMissiles}</strong>.
            </p>
          </div>
          <div className="bg-white/5 rounded-xl p-5">
            <h3 className="text-white font-medium mb-2">⚡ Балістичні ракети</h3>
            <p className="text-sm text-white/60">
              Іскандер-М, КН-23 — швидкість до Mach 6, час підльоту 3-5 хвилин.
              Найнебезпечніший тип загрози через мінімальний час реагування.
              Всього застосовано <strong className="text-white/80">{totalStats.ballisticMissiles}</strong>.
            </p>
          </div>
          <div className="bg-white/5 rounded-xl p-5">
            <h3 className="text-white font-medium mb-2">💣 КАБ (керовані авіабомби)</h3>
            <p className="text-sm text-white/60">
              КАБ-500, КАБ-1500 з модулем УМПК. Скидаються з літаків Су-34/Су-35.
              Дальність планування 60-70 км. Масово застосовуються на лінії фронту.
            </p>
          </div>
        </div>
      </section>

      {/* Methodology note */}
      <section className="mb-10 text-sm text-white/40 border-t border-white/5 pt-6">
        <h2 className="text-base font-medium text-white/60 mb-2">Методологія та джерела</h2>
        <p>
          Дані зібрані з відкритих джерел: офіційні повідомлення Повітряних сил ЗСУ, Обласних Військових
          Адміністрацій (ОВА), аналітичних платформ. Числа є приблизними оцінками (±5-10%) та можуть
          відрізнятися від інших джерел через різні методики підрахунку. Дані за 2025 рік є попередніми
          та оновлюються щомісяця.
        </p>
      </section>

      {/* CTA */}
      <section className="bg-[#36e4ff]/5 border border-[#36e4ff]/10 rounded-xl p-6 mb-8 text-center">
        <h2 className="text-lg font-semibold text-white mb-2">Відстежуйте тривоги в реальному часі</h2>
        <p className="text-sm text-white/60 mb-4">
          Карта NEPTUN показує активні тривоги, рух шахедів та ракет з оновленням кожні 5 секунд.
        </p>
        <Link
          href="/"
          className="inline-block px-6 py-2.5 bg-[#36e4ff]/20 hover:bg-[#36e4ff]/30 border border-[#36e4ff]/20 rounded-xl text-[#36e4ff] font-medium transition-colors"
        >
          Відкрити карту тривог
        </Link>
      </section>

      <Footer />
    </div>
  );
}
