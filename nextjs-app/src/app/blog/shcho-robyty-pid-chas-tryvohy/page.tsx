import type { Metadata } from 'next';
import Link from 'next/link';
import Footer from '@/components/Footer';

export const metadata: Metadata = {
  title: 'Що робити під час повітряної тривоги — покрокова інструкція | NEPTUN',
  description:
    'Повний гайд: як правильно діяти під час повітряної тривоги в Україні. Де шукати укриття, що взяти з собою, які додатки встановити, безпека дітей та домашніх тварин.',
  keywords:
    'що робити під час тривоги, повітряна тривога інструкція, де ховатися під час тривоги, укриття, безпека під час обстрілу',
  alternates: { canonical: 'https://neptun.in.ua/blog/shcho-robyty-pid-chas-tryvohy' },
  openGraph: {
    type: 'article',
    url: 'https://neptun.in.ua/blog/shcho-robyty-pid-chas-tryvohy',
    title: 'Що робити під час повітряної тривоги — інструкція',
    description: 'Покрокова інструкція дій під час повітряної тривоги в Україні.',
    images: [{ url: 'https://neptun.in.ua/api/og', width: 1200, height: 630 }],
    siteName: 'NEPTUN',
    locale: 'uk_UA',
  },
};

export default function Article() {
  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'BlogPosting',
    headline: 'Що робити під час повітряної тривоги — покрокова інструкція',
    url: 'https://neptun.in.ua/blog/shcho-robyty-pid-chas-tryvohy',
    datePublished: '2025-02-15',
    dateModified: '2025-02-15',
    author: { '@type': 'Organization', name: 'NEPTUN', url: 'https://neptun.in.ua' },
    publisher: { '@type': 'Organization', name: 'NEPTUN', url: 'https://neptun.in.ua' },
    description: 'Повний гайд дій під час повітряної тривоги в Україні.',
    inLanguage: 'uk',
    mainEntityOfPage: 'https://neptun.in.ua/blog/shcho-robyty-pid-chas-tryvohy',
    breadcrumb: {
      '@type': 'BreadcrumbList',
      itemListElement: [
        { '@type': 'ListItem', position: 1, name: 'Головна', item: 'https://neptun.in.ua/' },
        { '@type': 'ListItem', position: 2, name: 'Блог', item: 'https://neptun.in.ua/blog' },
        { '@type': 'ListItem', position: 3, name: 'Що робити під час тривоги', item: 'https://neptun.in.ua/blog/shcho-robyty-pid-chas-tryvohy' },
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
        <span className="text-white/60">Що робити під час тривоги</span>
      </nav>

      <article className="prose-invert">
        <div className="text-xs text-white/40 mb-3">
          <time dateTime="2025-02-15">15 лютого 2025</time> · 8 хв читання
        </div>

        <h1 className="text-3xl font-bold text-white mb-6">
          Що робити під час повітряної тривоги — покрокова інструкція
        </h1>

        <div className="space-y-4 text-[15px] leading-relaxed">
          <p>
            Повітряна тривога — це сигнал, який означає реальну загрозу ракетного або дронового удару.
            Від правильних дій у перші хвилини після сирени залежить ваша безпека та безпека вашої родини.
            У цій статті ми розповімо, що робити крок за кроком.
          </p>

          <h2 className="text-xl font-semibold text-white mt-8">1. Негайно прямуйте до укриття</h2>
          <p>
            Почувши сирену або отримавши push-сповіщення про тривогу, негайно прямуйте до найближчого
            укриття. Це може бути:
          </p>
          <ul className="list-disc pl-6 space-y-1.5">
            <li><strong className="text-white/90">Підвал будинку</strong> — найнадійніший варіант, особливо при ракетних ударах</li>
            <li><strong className="text-white/90">Станція метро</strong> — у містах з метрополітеном (Київ, Харків, Дніпро)</li>
            <li><strong className="text-white/90">Паркінг</strong> — підземний паркінг забезпечує гарний захист</li>
            <li><strong className="text-white/90">Коридор без вікон</strong> — якщо немає можливості дістатися до укриття</li>
            <li><strong className="text-white/90">Два стіни від зовнішньої стіни</strong> — мінімальний стандарт захисту</li>
          </ul>

          <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4 my-4">
            <p className="text-red-300 text-sm font-medium">
              ⚠️ НЕ ЗАЛИШАЙТЕСЬ біля вікон, на балконах, на верхніх поверхах або на відкритому повітрі під час тривоги!
            </p>
          </div>

          <h2 className="text-xl font-semibold text-white mt-8">2. Підготуйте &ldquo;тривожну валізу&rdquo;</h2>
          <p>
            Тривожна валіза — це сумка з необхідними речами, яка завжди має бути готова. Рекомендований вміст:
          </p>
          <ul className="list-disc pl-6 space-y-1.5">
            <li>Документи (паспорт, ID-картка, посвідчення водія) — оригінали або копії</li>
            <li>Заряджений павербанк та кабелі для зарядки</li>
            <li>Вода (мінімум 1 літр на особу) та нешвидкопсувна їжа</li>
            <li>Ліхтарик та батарейки</li>
            <li>Аптечка першої допомоги: бинти, джгут, знеболюючі</li>
            <li>Готівка (невеликі купюри)</li>
            <li>Теплий одяг (у холодну пору року)</li>
            <li>Необхідні медикаменти (якщо приймаєте постійно)</li>
          </ul>

          <h2 className="text-xl font-semibold text-white mt-8">3. Встановіть додатки для сповіщень</h2>
          <p>
            Мобільні додатки допомагають отримувати тривоги швидше, ніж вуличні сирени. Рекомендовані додатки:
          </p>
          <ul className="list-disc pl-6 space-y-1.5">
            <li>
              <strong className="text-white/90">NEPTUN</strong> — карта тривог з відстеженням шахедів
              та push-сповіщеннями (<a href="https://play.google.com/store/apps/details?id=com.neptunalarm.neptun_alarm_app" target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:text-blue-300">Google Play</a>,{' '}
              <a href="https://apps.apple.com/ua/app/%D0%BA%D0%B0%D1%80%D1%82%D0%B0-%D1%82%D1%80%D0%B8%D0%B2%D0%BE%D0%B3-dron-alerts/id6758108122?l=uk" target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:text-blue-300">App Store</a>)
            </li>
            <li><strong className="text-white/90">&ldquo;Повітряна тривога&rdquo;</strong> — офіційний додаток ДСНС</li>
            <li><strong className="text-white/90">Телеграм-канали ОВА</strong> — підпишіться на канал вашої обласної адміністрації</li>
          </ul>

          <h2 className="text-xl font-semibold text-white mt-8">4. Дії при різних типах загроз</h2>

          <h3 className="text-lg font-medium text-white mt-6">Балістичні ракети (Іскандер, КН-23)</h3>
          <p>
            Час підльоту — <strong className="text-white">3-5 хвилин</strong>. Це найнебезпечніший тип загрози.
            Негайно лягайте на підлогу, закрийте голову руками. Якщо є можливість — біжіть до підвалу.
          </p>

          <h3 className="text-lg font-medium text-white mt-6">Крилаті ракети (Х-101, Калібр)</h3>
          <p>
            Час підльоту — <strong className="text-white">30-90 хвилин</strong> залежно від регіону.
            Є час дістатися до укриття. Слідкуйте за повідомленнями Повітряних сил ЗСУ.
          </p>

          <h3 className="text-lg font-medium text-white mt-6">БПЛА &ldquo;Шахед&rdquo;</h3>
          <p>
            Швидкість ~180 км/год, летять групами. Тривога може тривати <strong className="text-white">кілька годин</strong>.
            Перебувайте в укритті. Використовуйте <Link href="/" className="text-blue-400 hover:text-blue-300">карту NEPTUN</Link> для відстеження траєкторій.
          </p>

          <h2 className="text-xl font-semibold text-white mt-8">5. Безпека дітей</h2>
          <p>
            Поясніть дітям, що робити під час тривоги, простими словами. Проведіть &ldquo;тренування&rdquo; —
            покажіть шлях до укриття. Тримайте ігри або книжки в тривожній валізі, щоб відволікти
            дитину під час очікування.
          </p>

          <h2 className="text-xl font-semibold text-white mt-8">6. Домашні тварини</h2>
          <p>
            Підготуйте переноску для кота або собаки. Тримайте корм і воду в тривожній валізі.
            Під час тривоги тварини можуть панікувати — тримайте їх у переносці або на повідку.
          </p>

          <h2 className="text-xl font-semibold text-white mt-8">7. Після відбою тривоги</h2>
          <ul className="list-disc pl-6 space-y-1.5">
            <li>Дочекайтесь офіційного відбою — не виходьте передчасно</li>
            <li>Перевірте стан житла (вікна, стіни, дах)</li>
            <li>Якщо бачите уламки або підозрілі предмети — не торкайтесь, викличте ДСНС (101)</li>
            <li>При виявленні пошкоджень газу або электрики — негайно повідомте аварійні служби</li>
          </ul>

          <h2 className="text-xl font-semibold text-white mt-8">Підсумок</h2>
          <p>
            Головне правило — <strong className="text-white">кожна тривога реальна</strong>. Не ігноруйте
            сирени та push-сповіщення. Підготуйте тривожну валізу, знайте шлях до укриття, встановіть
            додатки для моніторингу загроз. Відстежуйте ситуацію на{' '}
            <Link href="/" className="text-blue-400 hover:text-blue-300">карті тривог NEPTUN</Link> в реальному часі.
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
