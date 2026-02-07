import type { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'Про NEPTUN — Карта тривог України',
  description: 'NEPTUN — інтерактивна карта тривог України в реальному часі. Дізнайтеся більше про наш проєкт.',
};

export default function AboutPage() {
  return (
    <div className="min-h-screen bg-[#0a0e17] text-white/80 p-6 max-w-3xl mx-auto">
      <Link href="/" className="text-blue-400 hover:text-blue-300 text-sm mb-6 inline-block">
        &larr; Повернутися на карту
      </Link>

      <h1 className="text-3xl font-bold text-white mb-6">Про NEPTUN</h1>

      <div className="space-y-4 text-[15px] leading-relaxed">
        <p>
          <strong className="text-white">NEPTUN</strong> — це інтерактивна карта повітряних тривог
          та загроз України, яка працює в реальному часі 24/7.
        </p>

        <h2 className="text-xl font-semibold text-white mt-8">Що ми робимо</h2>
        <p>
          Ми автоматично збираємо інформацію з офіційних Telegram-каналів ОВА (Обласних Військових
          Адміністрацій) та інших відкритих джерел, обробляємо її та візуалізуємо на карті.
        </p>

        <h2 className="text-xl font-semibold text-white mt-8">Можливості</h2>
        <ul className="list-disc pl-6 space-y-2">
          <li>Карта повітряних тривог по всіх областях та районах</li>
          <li>Відстеження шахедів, дронів та ракет з траєкторіями</li>
          <li>Push-сповіщення про тривоги (Android додаток)</li>
          <li>Аналітика по регіонах</li>
          <li>Оновлення кожні 5-10 секунд</li>
        </ul>

        <h2 className="text-xl font-semibold text-white mt-8">Важливо</h2>
        <p>
          NEPTUN <strong className="text-white">не є офіційною</strong> системою оповіщення. Для
          офіційної інформації використовуйте державні ресурси та додаток &ldquo;Повітряна тривога&rdquo;.
        </p>
      </div>
    </div>
  );
}
