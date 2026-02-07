import type { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'Контакти — NEPTUN',
  description: 'Зв\'яжіться з командою NEPTUN.',
};

export default function ContactPage() {
  return (
    <div className="min-h-screen bg-[#0a0e17] text-white/80 p-6 max-w-3xl mx-auto">
      <Link href="/" className="text-blue-400 hover:text-blue-300 text-sm mb-6 inline-block">
        &larr; Повернутися на карту
      </Link>

      <h1 className="text-3xl font-bold text-white mb-6">Контакти</h1>

      <div className="space-y-4 text-[15px] leading-relaxed">
        <p>
          Маєте питання, пропозиції або знайшли помилку? Зв&apos;яжіться з нами!
        </p>

        <div className="bg-white/5 rounded-xl p-6 mt-6">
          <h2 className="text-lg font-semibold text-white mb-3">Telegram</h2>
          <a
            href="https://t.me/+aBR79kExNQM1ZjZi"
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-400 hover:text-blue-300 text-lg"
          >
            Написати в Telegram &rarr;
          </a>
        </div>
      </div>
    </div>
  );
}
