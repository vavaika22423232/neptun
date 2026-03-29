import type { Metadata } from 'next';
import Link from 'next/link';
import Footer from '@/components/Footer';

export const metadata: Metadata = {
  title: 'Блог — Карта тривог NEPTUN | Новини, поради, аналітика',
  description:
    'Блог NEPTUN: корисні статті про повітряні тривоги, безпеку під час обстрілів, налаштування push-сповіщень, порівняння карт тривог та типи повітряних загроз.',
  keywords:
    'блог тривоги, поради при тривозі, безпека при обстрілі, карта тривог блог, NEPTUN блог',
  alternates: {
    canonical: 'https://neptun.in.ua/blog',
  },
  openGraph: {
    type: 'website',
    url: 'https://neptun.in.ua/blog',
    title: 'Блог — NEPTUN',
    description: 'Корисні статті про повітряні тривоги, безпеку та налаштування сповіщень.',
    images: [{ url: 'https://neptun.in.ua/api/og', width: 1200, height: 630, alt: 'Блог NEPTUN' }],
    siteName: 'NEPTUN Карта тривог',
    locale: 'uk_UA',
  },
};

interface BlogPost {
  slug: string;
  title: string;
  description: string;
  date: string;
  readMin: number;
  tags: string[];
}

const posts: BlogPost[] = [
  {
    slug: 'shcho-robyty-pid-chas-tryvohy',
    title: 'Що робити під час повітряної тривоги — покрокова інструкція',
    description: 'Детальний гайд: як правильно діяти під час повітряної тривоги, де шукати укриття, що взяти з собою та які додатки встановити.',
    date: '2025-02-15',
    readMin: 8,
    tags: ['безпека', 'інструкція'],
  },
  {
    slug: 'yak-pratsyuye-karta-shahediv',
    title: 'Як працює карта шахедів NEPTUN — від Telegram до карти за 5 секунд',
    description: 'Технічний розбір: як NEPTUN збирає дані з Telegram-каналів ОВА, аналізує їх за допомогою ШІ та відображає траєкторії шахедів на карті.',
    date: '2025-02-10',
    readMin: 6,
    tags: ['технології', 'шахеди'],
  },
  {
    slug: 'typy-povitryanykh-zahroz',
    title: 'Типи повітряних загроз в Україні — шахеди, ракети, КАБ',
    description: 'Повний гайд по типах повітряних загроз: БПЛА Shahed, крилаті та балістичні ракети, КАБ. Швидкість, дальність, час реагування.',
    date: '2025-02-05',
    readMin: 7,
    tags: ['загрози', 'аналітика'],
  },
  {
    slug: 'yak-nalashtuvatу-push-spovishchennya',
    title: 'Як налаштувати push-сповіщення про тривоги — NEPTUN додаток',
    description: 'Покрокова інструкція: завантажити NEPTUN на Android/iOS, обрати регіон, налаштувати типи сповіщень та звук тривоги.',
    date: '2025-01-28',
    readMin: 5,
    tags: ['інструкція', 'додаток'],
  },
  {
    slug: 'porivnyannya-kart-tryvoh',
    title: 'Порівняння карт тривог України 2025 — NEPTUN vs інші сервіси',
    description: 'Об\'єктивне порівняння популярних карт тривог: швидкість оновлення, функціонал, мобільні додатки, зручність інтерфейсу.',
    date: '2025-01-20',
    readMin: 6,
    tags: ['порівняння', 'огляд'],
  },
];

export default function BlogPage() {
  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'Blog',
    name: 'Блог NEPTUN — Карта тривог',
    url: 'https://neptun.in.ua/blog',
    description: 'Блог NEPTUN: статті про повітряні тривоги, безпеку, технології та аналітику.',
    publisher: { '@type': 'Organization', name: 'NEPTUN', url: 'https://neptun.in.ua' },
    inLanguage: 'uk',
    blogPost: posts.map((p) => ({
      '@type': 'BlogPosting',
      headline: p.title,
      url: `https://neptun.in.ua/blog/${p.slug}`,
      datePublished: p.date,
      description: p.description,
      author: { '@type': 'Organization', name: 'NEPTUN' },
      publisher: { '@type': 'Organization', name: 'NEPTUN' },
      inLanguage: 'uk',
    })),
  };

  return (
    <div className="min-h-screen bg-[var(--surface-dim)] text-white/80 p-6 max-w-3xl mx-auto">
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />

      <Link href="/" className="text-blue-400 hover:text-blue-300 text-sm mb-6 inline-block">
        &larr; Повернутися на карту
      </Link>

      <h1 className="text-3xl font-bold text-white mb-2">Блог NEPTUN</h1>
      <p className="text-white/50 text-sm mb-8">
        Корисні статті про повітряні тривоги, безпеку та технології
      </p>

      <div className="space-y-6">
        {posts.map((post) => (
          <article key={post.slug} className="bg-white/5 rounded-xl p-5 hover:bg-white/[0.07] transition-colors border border-white/5">
            <Link href={`/blog/${post.slug}`} className="block no-underline">
              <div className="flex items-center gap-3 text-xs text-white/40 mb-2">
                <time dateTime={post.date}>
                  {new Date(post.date).toLocaleDateString('uk-UA', { day: 'numeric', month: 'long', year: 'numeric' })}
                </time>
                <span>·</span>
                <span>{post.readMin} хв читання</span>
              </div>
              <h2 className="text-lg font-semibold text-white mb-2 hover:text-[#36e4ff] transition-colors">
                {post.title}
              </h2>
              <p className="text-sm text-white/60">{post.description}</p>
              <div className="flex gap-2 mt-3">
                {post.tags.map((tag) => (
                  <span key={tag} className="text-xs px-2 py-0.5 bg-[#36e4ff]/10 text-[#36e4ff]/70 rounded-md">
                    {tag}
                  </span>
                ))}
              </div>
            </Link>
          </article>
        ))}
      </div>

      <Footer />
    </div>
  );
}
