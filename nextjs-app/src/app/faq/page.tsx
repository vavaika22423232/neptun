import type { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'FAQ — Карта тривог NEPTUN',
  description: 'Відповіді на часті питання про карту тривог NEPTUN.',
};

const faqItems = [
  { q: 'Що таке NEPTUN?', a: 'NEPTUN — це інтерактивна карта тривог України, яка автоматично збирає дані з відкритих джерел та візуалізує їх у реальному часі.' },
  { q: 'Чи є карта офіційною?', a: 'Ні, NEPTUN не є офіційною системою оповіщення. Для офіційної інформації використовуйте додаток "Повітряна тривога".' },
  { q: 'Як часто оновлюються дані?', a: 'Дані оновлюються кожні 5-10 секунд. Затримка залежить від швидкості публікації в джерелах.' },
  { q: 'Чи є мобільний додаток?', a: 'Так, безкоштовний Android-додаток доступний у Google Play. iOS версія в розробці.' },
  { q: 'Як підтримати проєкт?', a: 'Натисніть кнопку "Підтримати" на карті. Також допомагає поширення серед знайомих.' },
  { q: 'Що означають стрілки на карті?', a: 'Стрілки показують напрямок руху повітряних загроз (шахеди, ракети, дрони).' },
  { q: 'Чи працює карта без інтернету?', a: 'Для роботи потрібен інтернет. Мобільний додаток надсилає push-сповіщення навіть при слабкому зв\'язку.' },
];

export default function FaqPage() {
  return (
    <div className="min-h-screen bg-[#0a0e17] text-white/80 p-6 max-w-3xl mx-auto">
      <Link href="/" className="text-blue-400 hover:text-blue-300 text-sm mb-6 inline-block">
        &larr; Повернутися на карту
      </Link>

      <h1 className="text-3xl font-bold text-white mb-6">Часті питання (FAQ)</h1>

      <div className="space-y-4">
        {faqItems.map((item, i) => (
          <details key={i} className="group bg-white/5 rounded-xl p-4">
            <summary className="font-medium text-white cursor-pointer list-none flex items-center justify-between">
              {item.q}
              <span className="text-white/30 group-open:rotate-180 transition-transform">&#9660;</span>
            </summary>
            <p className="mt-3 text-white/60 text-sm leading-relaxed">{item.a}</p>
          </details>
        ))}
      </div>
    </div>
  );
}
