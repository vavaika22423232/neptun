'use client';

import { TELEGRAM_CHANNEL_URL } from '@/lib/constants';

interface FaqModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const faqItems = [
  {
    icon: 'map',
    question: 'Що таке NEPTUN?',
    answer:
      'NEPTUN — це інтерактивна карта тривог України, яка автоматично збирає дані з відкритих джерел (офіційні телеграм-канали ОВА та інші) та візуалізує їх у реальному часі.',
  },
  {
    icon: 'verified',
    question: 'Чи є карта офіційною?',
    answer:
      'Ні, NEPTUN не є офіційною системою оповіщення. Ми агрегуємо дані з публічних джерел для зручного відображення. Для офіційної інформації використовуйте державні ресурси та додаток "Повітряна тривога".',
  },
  {
    icon: 'schedule',
    question: 'Як швидко оновлюються дані?',
    answer:
      'Дані оновлюються автоматично кожні кілька секунд. Затримка залежить від швидкості публікації інформації в джерелах, які ми моніторимо.',
  },
  {
    icon: 'smartphone',
    question: 'Чи є мобільний додаток?',
    answer:
      'Так! Ви можете завантажити офіційний Android-додаток NEPTUN з Google Play. Додаток для iOS наразі в розробці.',
  },
  {
    icon: 'favorite',
    question: 'Як підтримати проєкт?',
    answer:
      'Ви можете підтримати нас фінансово через кнопку "Підтримати" у верхньому меню. Також допомагає поширення карти серед знайомих та позитивні відгуки в Google Play.',
  },
  {
    icon: 'flight',
    question: 'Що означають стрілки на карті?',
    answer:
      'Стрілки показують напрямок руху повітряних загроз (шахеди, ракети, дрони). Кожен тип загрози має свій колір та іконку.',
  },
  {
    icon: 'notifications',
    question: 'Як отримувати сповіщення про тривоги?',
    answer:
      'Встановіть наш Android-додаток з Google Play — він надсилає push-сповіщення про тривоги у вашому регіоні. Також можна підписатися на наш Telegram-канал.',
  },
  {
    icon: 'security',
    question: 'Наскільки безпечно користуватися картою?',
    answer:
      'Карта збирає лише публічні дані і не вимагає реєстрації. Ми не збираємо особисту інформацію користувачів.',
  },
  {
    icon: 'language',
    question: 'В яких регіонах працює карта?',
    answer:
      'Карта охоплює всі області України — від Закарпаття до Луганщини. Ми відстежуємо тривоги в усіх 24 областях, а також у Києві.',
  },
];

export default function FaqModal({ isOpen, onClose }: FaqModalProps) {
  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-[10000] flex items-center justify-center bg-black/60 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="bg-[#1c1c1e] rounded-2xl p-6 max-w-lg w-[90%] max-h-[85vh] overflow-y-auto relative"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          onClick={onClose}
          className="absolute top-3 right-4 text-white/50 hover:text-white text-2xl cursor-pointer bg-transparent border-none"
        >
          &times;
        </button>

        <div className="flex items-center gap-2 mb-4">
          <span className="material-icons text-white/60">help_outline</span>
          <h3 className="text-lg font-medium text-white">FAQ та правила використання</h3>
        </div>

        <div className="space-y-3">
          {faqItems.map((item, i) => (
            <details key={i} className="group">
              <summary className="flex items-center gap-2 text-white/80 text-[13px] font-medium cursor-pointer list-none py-2 px-3 bg-white/5 rounded-lg hover:bg-white/8 transition-colors">
                <span className="material-icons text-[16px] text-white/50">{item.icon}</span>
                {item.question}
                <span className="material-icons text-[16px] text-white/30 ml-auto group-open:rotate-180 transition-transform">
                  expand_more
                </span>
              </summary>
              <div className="text-white/50 text-[12px] leading-relaxed px-3 py-2 pl-8">
                {item.answer}
              </div>
            </details>
          ))}
        </div>

        <div className="mt-4 text-center">
          <a
            href={TELEGRAM_CHANNEL_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 text-blue-400 hover:text-blue-300 text-sm transition-colors"
          >
            <span className="material-icons text-[16px]">telegram</span>
            Зв&apos;язатися з нами в Telegram
          </a>
        </div>
      </div>
    </div>
  );
}
