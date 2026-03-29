import Link from 'next/link';

export default function NotFound() {
  return (
    <div className="min-h-screen bg-[var(--surface-dim)] text-white flex flex-col items-center justify-center p-6 text-center">
      <p className="text-6xl font-bold text-white/20 mb-2">404</p>
      <h1 className="text-2xl font-bold mb-3">Сторінку не знайдено</h1>
      <p className="text-white/50 max-w-md mb-6">
        Ця сторінка не існує або була переміщена. Скористайтесь посиланнями нижче.
      </p>
      <div className="flex flex-wrap gap-3 justify-center">
        <Link
          href="/"
          className="bg-blue-500 hover:bg-blue-600 text-white px-5 py-2.5 rounded-xl font-medium transition-colors"
        >
          Карта тривог
        </Link>
        <Link
          href="/karta-shahediv"
          className="bg-white/10 hover:bg-white/15 text-white/80 px-5 py-2.5 rounded-xl transition-colors"
        >
          Карта шахедів
        </Link>
        <Link
          href="/faq"
          className="bg-white/10 hover:bg-white/15 text-white/80 px-5 py-2.5 rounded-xl transition-colors"
        >
          FAQ
        </Link>
      </div>
      <div className="mt-8 flex flex-wrap gap-3 text-sm text-white/30 justify-center">
        <Link href="/karta-tryvoh" className="hover:text-white/50">Карта тривог</Link>
        <Link href="/radar-shahediv" className="hover:text-white/50">Радар шахедів</Link>
        <Link href="/about" className="hover:text-white/50">Про проєкт</Link>
        <Link href="/contact" className="hover:text-white/50">Контакти</Link>
      </div>
    </div>
  );
}
