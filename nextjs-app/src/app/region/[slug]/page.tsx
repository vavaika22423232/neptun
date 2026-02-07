import type { Metadata } from 'next';
import Link from 'next/link';

const regionNames: Record<string, string> = {
  kyiv: 'Київ',
  kyivska: 'Київська область',
  kharkivska: 'Харківська область',
  odeska: 'Одеська область',
  dnipropetrovska: 'Дніпропетровська область',
  zaporizka: 'Запорізька область',
  lvivska: 'Львівська область',
  mykolaivska: 'Миколаївська область',
  khersonska: 'Херсонська область',
  poltavska: 'Полтавська область',
  vinnytska: 'Вінницька область',
  cherkaska: 'Черкаська область',
  zhytomyrska: 'Житомирська область',
  sumska: 'Сумська область',
  chernihivska: 'Чернігівська область',
  rivnenska: 'Рівненська область',
  volynska: 'Волинська область',
  ternopilska: 'Тернопільська область',
  'ivano-frankivska': 'Івано-Франківська область',
  zakarpatska: 'Закарпатська область',
  chernivetska: 'Чернівецька область',
  khmelnytska: 'Хмельницька область',
  kirovohradska: 'Кіровоградська область',
  donetska: 'Донецька область',
  luhanska: 'Луганська область',
};

interface PageProps {
  params: Promise<{ slug: string }>;
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { slug } = await params;
  const regionName = regionNames[slug] || slug;
  return {
    title: `Тривога ${regionName} — Карта тривог NEPTUN`,
    description: `Повітряна тривога ${regionName} онлайн. Дивіться актуальні тривоги та загрози на карті NEPTUN.`,
  };
}

export async function generateStaticParams() {
  return Object.keys(regionNames).map((slug) => ({ slug }));
}

export default async function RegionPage({ params }: PageProps) {
  const { slug } = await params;
  const regionName = regionNames[slug] || slug;

  return (
    <div className="min-h-screen bg-[#0a0e17] text-white/80 p-6 max-w-3xl mx-auto">
      <Link href="/" className="text-blue-400 hover:text-blue-300 text-sm mb-6 inline-block">
        &larr; Повернутися на карту
      </Link>

      <h1 className="text-3xl font-bold text-white mb-4">
        Тривога {regionName}
      </h1>

      <p className="text-lg mb-6">
        Актуальна карта тривог для {regionName}. Дані оновлюються в реальному часі.
      </p>

      <Link
        href="/"
        className="inline-flex items-center gap-2 bg-blue-500 hover:bg-blue-600 text-white px-6 py-3 rounded-xl font-medium transition-colors"
      >
        Відкрити карту тривог &rarr;
      </Link>

      <div className="mt-8 space-y-3 text-sm text-white/50">
        <h2 className="text-lg font-semibold text-white/80">Інші регіони</h2>
        <div className="flex flex-wrap gap-2">
          {Object.entries(regionNames).map(([s, name]) => (
            <Link
              key={s}
              href={`/region/${s}`}
              className={`px-3 py-1.5 rounded-lg text-xs transition-colors ${
                s === slug
                  ? 'bg-blue-500/20 text-blue-400'
                  : 'bg-white/5 text-white/50 hover:bg-white/10'
              }`}
            >
              {name}
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
