import type { Metadata } from 'next';
import Link from 'next/link';
import Footer from '@/components/Footer';

export const metadata: Metadata = {
  title: 'Карта шахедів онлайн — відстеження шахедів в реальному часі | NEPTUN',
  description:
    'Карта шахедів України онлайн. Відстежуйте рух шахедів, дронів Shahed-136/131 в реальному часі на інтерактивній мапі. Траєкторії БПЛА, напрямок польоту, швидкість — 24/7.',
  keywords:
    'карта шахедів, карта шахедов, мапа шахедів, мапа шахедов, шахеди онлайн, шахеди карта, відстеження шахедів, shahed map, shahed tracker',
  alternates: {
    canonical: 'https://neptun.in.ua/karta-shahediv',
  },
  openGraph: {
    type: 'website',
    url: 'https://neptun.in.ua/karta-shahediv',
    title: 'Карта шахедів онлайн — NEPTUN',
    description: 'Відстежуйте рух шахедів, дронів та БПЛА на інтерактивній карті України в реальному часі.',
    images: [{ url: 'https://neptun.in.ua/api/og', width: 1200, height: 630, alt: 'Карта шахедів онлайн — NEPTUN' }],
    siteName: 'NEPTUN Карта тривог',
    locale: 'uk_UA',
  },
};

export default function KartaShahedivPage() {
  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'WebPage',
    name: 'Карта шахедів онлайн — NEPTUN',
    url: 'https://neptun.in.ua/karta-shahediv',
    description: 'Інтерактивна карта шахедів України з відстеженням БПЛА, дронів Shahed-136/131 в реальному часі.',
    isPartOf: { '@type': 'WebSite', name: 'NEPTUN', url: 'https://neptun.in.ua' },
    breadcrumb: {
      '@type': 'BreadcrumbList',
      itemListElement: [
        { '@type': 'ListItem', position: 1, name: 'Головна', item: 'https://neptun.in.ua' },
        { '@type': 'ListItem', position: 2, name: 'Карта шахедів', item: 'https://neptun.in.ua/karta-shahediv' },
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
        Карта шахедів онлайн — відстеження дронів в реальному часі
      </h1>

      <p className="text-lg text-white/70 mb-6">
        Інтерактивна карта шахедів України від NEPTUN. Дивіться рух дронів-камікадзе Shahed-136/131,
        їхні траєкторії та напрямок польоту в реальному часі на карті.
      </p>

      <Link
        href="/"
        className="inline-flex items-center gap-2 bg-blue-500 hover:bg-blue-600 text-white px-6 py-3 rounded-xl font-medium transition-colors mb-8"
      >
        Відкрити карту шахедів &rarr;
      </Link>

      <article className="text-white/70 leading-relaxed space-y-6">
        <section>
          <h2 className="text-xl font-semibold text-white/90 mb-3">Що таке карта шахедів?</h2>
          <p>
            <strong className="text-white">Карта шахедів</strong> (також відома як «мапа шахедів» або «шахед трекер») — це
            інтерактивна онлайн-карта, яка показує реальний рух безпілотних літальних апаратів (БПЛА) Shahed-136 та Shahed-131
            над територією України. На відміну від звичайної <Link href="/karta-tryvoh" className="text-blue-400 hover:underline">карти тривог</Link>,
            яка показує лише статус сирени по регіонах, карта шахедів відображає:
          </p>
          <ul className="list-disc pl-6 space-y-2 mt-3">
            <li><strong className="text-white">Точне місцезнаходження</strong> — де саме зафіксовано шахед або групу шахедів</li>
            <li><strong className="text-white">Напрямок польоту</strong> — куди летить дрон, його курс та можливі цілі</li>
            <li><strong className="text-white">Траєкторію</strong> — маршрут, яким рухається шахед від точки запуску</li>
            <li><strong className="text-white">Тип загрози</strong> — шахед, розвідувальний БПЛА, КАБ або інший тип дрона</li>
            <li><strong className="text-white">Кількість</strong> — скільки шахедів у групі зафіксовано</li>
          </ul>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-white/90 mb-3">Як працює відстеження шахедів на NEPTUN?</h2>
          <p>
            Система NEPTUN автоматично збирає повідомлення з десятків офіційних Telegram-каналів — обласних військових
            адміністрацій (ОВА), моніторингових груп та інших перевірених джерел. Кожне повідомлення аналізується
            за допомогою штучного інтелекту, який визначає:
          </p>
          <ul className="list-disc pl-6 space-y-1 mt-3">
            <li>Тип загрози (шахед, ракета, БПЛА, КАБ)</li>
            <li>Географічне розташування (область, район, населений пункт)</li>
            <li>Напрямок руху та курс</li>
            <li>Кількість об&apos;єктів у групі</li>
            <li>Точку запуску (Чорне море, Крим, Краснодарський край тощо)</li>
          </ul>
          <p className="mt-3">
            Після обробки загроза миттєво з&apos;являється на карті — зазвичай протягом 5-10 секунд після публікації
            першоджерела. Координати визначаються через геокодування з базою понад 30 000 населених пунктів України.
          </p>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-white/90 mb-3">Типи загроз на карті шахедів</h2>
          <div className="grid sm:grid-cols-2 gap-4">
            <div className="bg-white/5 rounded-xl p-4">
              <h3 className="font-medium text-white mb-1">🔴 Шахеди (Shahed-136/131)</h3>
              <p className="text-sm">Дрони-камікадзе іранського виробництва. Летять повільно (150-180 км/год), але великими групами. Основна нічна загроза.</p>
            </div>
            <div className="bg-white/5 rounded-xl p-4">
              <h3 className="font-medium text-white mb-1">🟡 Розвідувальні БПЛА</h3>
              <p className="text-sm">Безпілотники для розвідки. Зазвичай поодинокі, літають на великій висоті.</p>
            </div>
            <div className="bg-white/5 rounded-xl p-4">
              <h3 className="font-medium text-white mb-1">🔵 Крилаті ракети</h3>
              <p className="text-sm">Х-101, Калібр — швидкісні цілі. З&apos;являються на карті з позначкою траєкторії.</p>
            </div>
            <div className="bg-white/5 rounded-xl p-4">
              <h3 className="font-medium text-white mb-1">⚫ КАБ (керовані авіабомби)</h3>
              <p className="text-sm">Авіабомби з модулями наведення. Зазвичай використовуються поблизу лінії фронту.</p>
            </div>
          </div>
        </section>

        <section>
          <h2 className="text-xl font-semibold text-white/90 mb-3">Де дивитися карту шахедів?</h2>
          <p>
            Карта шахедів NEPTUN доступна безкоштовно на <Link href="/" className="text-blue-400 hover:underline">neptun.in.ua</Link>.
            Також доступний мобільний додаток з push-сповіщеннями:
          </p>
          <div className="flex flex-wrap gap-3 mt-3">
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
          <h2 className="text-xl font-semibold text-white/90 mb-3">Чим відрізняється від інших карт?</h2>
          <ul className="list-disc pl-6 space-y-2">
            <li><strong className="text-white">Швидкість</strong> — дані з&apos;являються на карті за 5-10 секунд після публікації в джерелі</li>
            <li><strong className="text-white">ШІ-аналітика</strong> — автоматичне визначення типу загрози, напрямку, траєкторії</li>
            <li><strong className="text-white">Ланцюжки повідомлень</strong> — follow-up повідомлення оновлюють існуючий маркер, а не створюють новий</li>
            <li><strong className="text-white">Безкоштовно</strong> — без підписок, реклами та обмежень</li>
          </ul>
        </section>
      </article>

      {/* Related pages */}
      <div className="mt-6 p-4 bg-white/5 rounded-xl text-sm">
        <h3 className="font-medium text-white mb-2">Корисні посилання</h3>
        <div className="flex flex-wrap gap-3 text-white/50">
          <Link href="/povitryana-tryvoga" className="text-blue-400 hover:underline">Повітряна тривога</Link>
          <Link href="/tryvoga-zaraz" className="text-blue-400 hover:underline">Тривога зараз</Link>
          <Link href="/karta-tryvoh" className="text-blue-400 hover:underline">Карта тривог</Link>
          <Link href="/radar-shahediv" className="text-blue-400 hover:underline">Радар шахедів</Link>
          <Link href="/faq" className="text-blue-400 hover:underline">FAQ</Link>
          <Link href="/about" className="text-blue-400 hover:underline">Про проєкт</Link>
        </div>
      </div>

      {/* Region quick links */}
      <div className="mt-8 text-sm">
        <h2 className="text-lg font-semibold text-white/80 mb-3">Шахеди по областях</h2>
        <p className="text-white/50 mb-3">Дивіться актуальну інформацію про шахеди та тривоги у вашому регіоні:</p>
        <div className="flex flex-wrap gap-2">
          {['kyiv', 'kharkivska', 'odeska', 'dnipropetrovska', 'zaporizka', 'lvivska', 'mykolaivska', 'khersonska', 'sumska', 'poltavska', 'vinnytska', 'cherkaska'].map((slug) => (
            <Link
              key={slug}
              href={`/region/${slug}`}
              className="px-3 py-1.5 rounded-lg text-xs bg-white/5 text-white/50 hover:bg-white/10 transition-colors"
            >
              {slug === 'kyiv' ? 'Київ' : slug.charAt(0).toUpperCase() + slug.slice(1).replace('ska', 'ська')}
            </Link>
          ))}
        </div>
      </div>

      <Footer />
    </div>
  );
}
