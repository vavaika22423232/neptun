import type { Metadata } from 'next';
import Link from 'next/link';
import Footer from '@/components/Footer';

export const metadata: Metadata = {
  title: 'Політика конфіденційності — NEPTUN',
  description: 'Політика конфіденційності карти тривог NEPTUN.',
};

export default function PrivacyPage() {
  return (
    <div className="min-h-screen bg-[var(--surface-dim)] text-white/80 p-6 max-w-3xl mx-auto overflow-y-auto">
      <Link href="/" className="text-blue-400 hover:text-blue-300 text-sm mb-6 inline-block">
        &larr; Повернутися на карту
      </Link>

      <h1 className="text-3xl font-bold text-white mb-6">Політика конфіденційності</h1>

      <div className="space-y-4 text-[15px] leading-relaxed">
        <p>Останнє оновлення: Лютий 2026</p>

        <h2 className="text-xl font-semibold text-white mt-6">Які дані ми збираємо</h2>
        <ul className="list-disc pl-6 space-y-1">
          <li>Анонімний ідентифікатор сесії (для підрахунку онлайну)</li>
          <li>Тип платформи (веб/Android)</li>
          <li>Google Analytics (анонімна аналітика)</li>
        </ul>

        <h2 className="text-xl font-semibold text-white mt-6">Чого ми НЕ збираємо</h2>
        <ul className="list-disc pl-6 space-y-1">
          <li>Особисті дані (ім&apos;я, email, телефон)</li>
          <li>Геолокацію користувача</li>
          <li>Дані для реклами</li>
        </ul>

        <h2 className="text-xl font-semibold text-white mt-6">Cookies</h2>
        <p>
          Ми використовуємо localStorage для кешування даних карти та збереження налаштувань.
          Google Analytics використовує cookies для анонімної аналітики.
        </p>

        <h2 className="text-xl font-semibold text-white mt-6">Контакт</h2>
        <p>
          З питань конфіденційності звертайтесь через{' '}
          <a href="https://t.me/+aBR79kExNQM1ZjZi" className="text-blue-400 hover:text-blue-300">
            Telegram
          </a>.
        </p>
      </div>
      <Footer />
    </div>
  );
}
