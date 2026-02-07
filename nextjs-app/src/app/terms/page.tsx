import type { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'Умови використання — NEPTUN',
  description: 'Умови використання карти тривог NEPTUN.',
};

export default function TermsPage() {
  return (
    <div className="min-h-screen bg-[#0a0e17] text-white/80 p-6 max-w-3xl mx-auto overflow-y-auto">
      <Link href="/" className="text-blue-400 hover:text-blue-300 text-sm mb-6 inline-block">
        &larr; Повернутися на карту
      </Link>

      <h1 className="text-3xl font-bold text-white mb-6">Умови використання</h1>

      <div className="space-y-4 text-[15px] leading-relaxed">
        <h2 className="text-xl font-semibold text-white">1. Загальні положення</h2>
        <p>
          NEPTUN надає інформаційний сервіс &mdash; карту повітряних тривог та загроз України.
          Сервіс не є офіційною системою оповіщення.
        </p>

        <h2 className="text-xl font-semibold text-white mt-6">2. Джерела даних</h2>
        <p>
          Дані збираються з публічних Telegram-каналів та офіційного API тривог.
          Ми не гарантуємо 100% точність та актуальність інформації.
        </p>

        <h2 className="text-xl font-semibold text-white mt-6">3. Відповідальність</h2>
        <p>
          Для прийняття рішень щодо безпеки використовуйте офіційні джерела та додаток
          &ldquo;Повітряна тривога&rdquo; від Міністерства цифрової трансформації України.
        </p>

        <h2 className="text-xl font-semibold text-white mt-6">4. Контакт</h2>
        <p>
          З питаннями звертайтесь через{' '}
          <a href="https://t.me/+aBR79kExNQM1ZjZi" className="text-blue-400 hover:text-blue-300">
            Telegram
          </a>.
        </p>
      </div>
    </div>
  );
}
