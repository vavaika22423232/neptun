import type { Metadata } from 'next';
import Link from 'next/link';
import Footer from '@/components/Footer';

export const metadata: Metadata = {
  title: 'Типи повітряних загроз в Україні — шахеди, ракети, КАБ | NEPTUN',
  description:
    'Повний гайд по типах повітряних загроз: БПЛА Shahed-136/131, крилаті ракети Х-101/Калібр, балістичні ракети Іскандер, КАБ. Характеристики, швидкість, час реагування.',
  keywords:
    'типи повітряних загроз, шахед характеристики, крилаті ракети Україна, балістичні ракети, КАБ, БПЛА загрози',
  alternates: { canonical: 'https://neptun.in.ua/blog/typy-povitryanykh-zahroz' },
  openGraph: {
    type: 'article',
    url: 'https://neptun.in.ua/blog/typy-povitryanykh-zahroz',
    title: 'Типи повітряних загроз в Україні',
    description: 'Шахеди, крилаті та балістичні ракети, КАБ — характеристики та час реагування.',
    images: [{ url: 'https://neptun.in.ua/api/og', width: 1200, height: 630 }],
    siteName: 'NEPTUN',
    locale: 'uk_UA',
  },
};

export default function Article() {
  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'BlogPosting',
    headline: 'Типи повітряних загроз в Україні — шахеди, ракети, КАБ',
    url: 'https://neptun.in.ua/blog/typy-povitryanykh-zahroz',
    datePublished: '2025-02-05',
    dateModified: '2025-02-05',
    author: { '@type': 'Organization', name: 'NEPTUN', url: 'https://neptun.in.ua' },
    publisher: { '@type': 'Organization', name: 'NEPTUN', url: 'https://neptun.in.ua' },
    inLanguage: 'uk',
    mainEntityOfPage: 'https://neptun.in.ua/blog/typy-povitryanykh-zahroz',
    breadcrumb: {
      '@type': 'BreadcrumbList',
      itemListElement: [
        { '@type': 'ListItem', position: 1, name: 'Головна', item: 'https://neptun.in.ua/' },
        { '@type': 'ListItem', position: 2, name: 'Блог', item: 'https://neptun.in.ua/blog' },
        { '@type': 'ListItem', position: 3, name: 'Типи загроз', item: 'https://neptun.in.ua/blog/typy-povitryanykh-zahroz' },
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
        <span className="text-white/60">Типи повітряних загроз</span>
      </nav>

      <article>
        <div className="text-xs text-white/40 mb-3">
          <time dateTime="2025-02-05">5 лютого 2025</time> · 7 хв читання
        </div>

        <h1 className="text-3xl font-bold text-white mb-6">
          Типи повітряних загроз в Україні — шахеди, ракети, КАБ
        </h1>

        <div className="space-y-4 text-[15px] leading-relaxed">
          <p>
            З початку повномасштабного вторгнення Росія використовує різні типи повітряного озброєння
            для атак на цивільну інфраструктуру України. Розуміння характеристик кожного типу загрози
            допоможе вам правильно оцінити ризик та прийняти рішення під час{' '}
            <Link href="/karta-tryvoh" className="text-blue-400 hover:text-blue-300">повітряної тривоги</Link>.
          </p>

          {/* Shaheds */}
          <h2 className="text-xl font-semibold text-white mt-8">🛩️ БПЛА &ldquo;Шахед&rdquo; (Shahed-136/131)</h2>
          <div className="bg-white/5 rounded-xl p-5 my-3">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center text-sm">
              <div><div className="text-orange-400 font-bold">~180 км/год</div><div className="text-white/40 text-xs">Швидкість</div></div>
              <div><div className="text-orange-400 font-bold">~2 500 км</div><div className="text-white/40 text-xs">Дальність</div></div>
              <div><div className="text-orange-400 font-bold">40-50 кг</div><div className="text-white/40 text-xs">Бойова частина</div></div>
              <div><div className="text-orange-400 font-bold">2-6 годин</div><div className="text-white/40 text-xs">Тривалість тривоги</div></div>
            </div>
          </div>
          <p>
            Іранські безпілотники-камікадзе — найбільш масовий тип загрози. Росія запускає їх
            групами від 10 до 180+ одиниць, переважно вночі. Шахеди летять повільно та на малій
            висоті, що ускладнює їх виявлення радарами, але дає час для укриття.
          </p>
          <p>
            Шахеди часто використовуються як &ldquo;розвідники&rdquo; — вони виснажують ППО перед
            основним ракетним ударом. На <Link href="/karta-shahediv" className="text-blue-400 hover:text-blue-300">карті шахедів NEPTUN</Link> ви
            можете відстежувати їх траєкторії в реальному часі.
          </p>

          {/* Cruise missiles */}
          <h2 className="text-xl font-semibold text-white mt-8">🚀 Крилаті ракети</h2>
          <div className="bg-white/5 rounded-xl p-5 my-3">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center text-sm">
              <div><div className="text-red-400 font-bold">~900 км/год</div><div className="text-white/40 text-xs">Швидкість</div></div>
              <div><div className="text-red-400 font-bold">1 500-2 500 км</div><div className="text-white/40 text-xs">Дальність</div></div>
              <div><div className="text-red-400 font-bold">400-450 кг</div><div className="text-white/40 text-xs">Бойова частина</div></div>
              <div><div className="text-red-400 font-bold">30-90 хв</div><div className="text-white/40 text-xs">Час підльоту</div></div>
            </div>
          </div>
          <p>
            Основні типи: <strong className="text-white/90">Х-101/Х-555</strong> (запускаються зі стратегічних
            бомбардувальників Ту-95МС), <strong className="text-white/90">Калібр</strong> (морського базування,
            з кораблів Чорноморського флоту), <strong className="text-white/90">Х-22/Х-32</strong> (старіші ракети з Ту-22М3).
          </p>
          <p>
            Крилаті ракети маневрують на малій висоті та можуть змінювати курс в польоті.
            Час підльоту дає можливість дістатися до укриття, якщо тривога оголошена вчасно.
          </p>

          {/* Ballistic */}
          <h2 className="text-xl font-semibold text-white mt-8">⚡ Балістичні ракети</h2>
          <div className="bg-white/5 rounded-xl p-5 my-3">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center text-sm">
              <div><div className="text-purple-400 font-bold">Mach 5-6</div><div className="text-white/40 text-xs">Швидкість</div></div>
              <div><div className="text-purple-400 font-bold">300-500 км</div><div className="text-white/40 text-xs">Дальність</div></div>
              <div><div className="text-purple-400 font-bold">480 кг</div><div className="text-white/40 text-xs">Бойова частина</div></div>
              <div><div className="text-purple-400 font-bold">3-5 хв</div><div className="text-white/40 text-xs">Час підльоту</div></div>
            </div>
          </div>
          <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4 my-3">
            <p className="text-red-300 text-sm font-medium">
              ⚠️ Балістичні ракети — найнебезпечніший тип загрози. Час реагування мінімальний — 3-5 хвилин!
            </p>
          </div>
          <p>
            <strong className="text-white/90">Іскандер-М</strong> та <strong className="text-white/90">КН-23</strong> (північнокорейського виробництва) —
            оперативно-тактичні ракети з надзвуковою швидкістю. Запускаються з наземних
            мобільних комплексів на відстані 300-500 км від цілі. Практично не перехоплюються
            стандартними засобами ППО.
          </p>

          {/* KAB */}
          <h2 className="text-xl font-semibold text-white mt-8">💣 КАБ (керовані авіабомби)</h2>
          <div className="bg-white/5 rounded-xl p-5 my-3">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center text-sm">
              <div><div className="text-yellow-400 font-bold">~900 км/год</div><div className="text-white/40 text-xs">Швидкість</div></div>
              <div><div className="text-yellow-400 font-bold">60-70 км</div><div className="text-white/40 text-xs">Дальність</div></div>
              <div><div className="text-yellow-400 font-bold">до 1 500 кг</div><div className="text-white/40 text-xs">Маса бомби</div></div>
              <div><div className="text-yellow-400 font-bold">~5 хв</div><div className="text-white/40 text-xs">Час підльоту</div></div>
            </div>
          </div>
          <p>
            <strong className="text-white/90">КАБ-500</strong> та <strong className="text-white/90">КАБ-1500</strong> —
            авіабомби з модулем планування УМПК. Скидаються з літаків Су-34 та Су-35 на відстані 60-70 км
            від цілі, що дозволяє літакам не входити в зону ураження ППО.
          </p>
          <p>
            КАБ масово застосовуються на лінії фронту та в прифронтових областях — Харківській,
            Запорізькій, Донецькій, Херсонській. Через невелику дальність їх використання обмежене
            прифронтовою зоною.
          </p>

          {/* Recon UAVs */}
          <h2 className="text-xl font-semibold text-white mt-8">👁️ Розвідувальні БПЛА</h2>
          <p>
            Крім ударних дронів, Росія використовує розвідувальні БПЛА типу <strong className="text-white/90">ZALA</strong>,{' '}
            <strong className="text-white/90">Орлан-10</strong> та інші. Вони не несуть
            бойового навантаження, але збирають розвідувальні дані для наступних ударів.
            При виявленні розвідувальних БПЛА також може оголошуватися тривога.
          </p>

          {/* Combined attacks */}
          <h2 className="text-xl font-semibold text-white mt-8">Комбіновані атаки</h2>
          <p>
            Найнебезпечнішими є комбіновані атаки, коли Росія одночасно використовує кілька типів
            озброєння. Типовий сценарій:
          </p>
          <ol className="list-decimal pl-6 space-y-1.5">
            <li>Спочатку запускаються <strong className="text-white/90">шахеди</strong> — для виснаження ППО та відволікання</li>
            <li>Потім — <strong className="text-white/90">крилаті ракети</strong> для ураження енергетичної інфраструктури</li>
            <li>На фінальному етапі — <strong className="text-white/90">балістичні ракети</strong> по критичних об&rsquo;єктах</li>
          </ol>
          <p>
            Такі атаки найскладніші для ППО та вимагають максимальної уваги від цивільного населення.
          </p>

          {/* Summary table */}
          <h2 className="text-xl font-semibold text-white mt-8">Порівняльна таблиця</h2>
          <div className="overflow-x-auto my-3">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/10 text-white/50">
                  <th className="py-2 px-3 text-left font-medium">Тип</th>
                  <th className="py-2 px-3 text-right font-medium">Швидкість</th>
                  <th className="py-2 px-3 text-right font-medium">Час реагування</th>
                  <th className="py-2 px-3 text-right font-medium">Небезпека</th>
                </tr>
              </thead>
              <tbody>
                <tr className="border-b border-white/5"><td className="py-2 px-3">Шахед</td><td className="py-2 px-3 text-right">180 км/год</td><td className="py-2 px-3 text-right text-green-400">Години</td><td className="py-2 px-3 text-right">●●○○○</td></tr>
                <tr className="border-b border-white/5"><td className="py-2 px-3">Крилата ракета</td><td className="py-2 px-3 text-right">900 км/год</td><td className="py-2 px-3 text-right text-yellow-400">30-90 хв</td><td className="py-2 px-3 text-right">●●●○○</td></tr>
                <tr className="border-b border-white/5"><td className="py-2 px-3">Балістична</td><td className="py-2 px-3 text-right">Mach 5-6</td><td className="py-2 px-3 text-right text-red-400">3-5 хв</td><td className="py-2 px-3 text-right">●●●●●</td></tr>
                <tr className="border-b border-white/5"><td className="py-2 px-3">КАБ</td><td className="py-2 px-3 text-right">900 км/год</td><td className="py-2 px-3 text-right text-red-400">~5 хв</td><td className="py-2 px-3 text-right">●●●●○</td></tr>
              </tbody>
            </table>
          </div>

          <h2 className="text-xl font-semibold text-white mt-8">Як захиститися</h2>
          <p>
            Незалежно від типу загрози, головне правило — <strong className="text-white">не ігноруйте тривогу</strong>.
            Встановіть <Link href="/" className="text-blue-400 hover:text-blue-300">карту NEPTUN</Link> та додаток для push-сповіщень,
            щоб отримувати інформацію про тип загрози та приймати правильні рішення.
            Детальну інструкцію дій читайте у статті{' '}
            <Link href="/blog/shcho-robyty-pid-chas-tryvohy" className="text-blue-400 hover:text-blue-300">
              &ldquo;Що робити під час тривоги&rdquo;
            </Link>.
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
