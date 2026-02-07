'use client';

import { useEffect } from 'react';
import { TELEGRAM_CHANNEL_URL } from '@/lib/constants';

interface FaqModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const faqItems = [
  { icon: 'map', question: 'Що таке NEPTUN?', answer: 'NEPTUN — це інтерактивна карта тривог України, яка збирає дані з відкритих джерел та візуалізує їх у реальному часі.' },
  { icon: 'verified', question: 'Чи є карта офіційною?', answer: 'Ні, NEPTUN не є офіційною системою оповіщення. Для офіційної інформації використовуйте додаток "Повітряна тривога".' },
  { icon: 'schedule', question: 'Як швидко оновлюються дані?', answer: 'Дані оновлюються кожні кілька секунд. Затримка залежить від швидкості джерел.' },
  { icon: 'smartphone', question: 'Чи є мобільний додаток?', answer: 'Так! Android-додаток доступний у Google Play. iOS — в розробці.' },
  { icon: 'favorite', question: 'Як підтримати проєкт?', answer: 'Через кнопку "Донат" або поширенням карти серед знайомих.' },
  { icon: 'flight', question: 'Що означають стрілки?', answer: 'Напрямок руху повітряних загроз. Кожен тип має свій колір та іконку.' },
  { icon: 'notifications', question: 'Як отримувати сповіщення?', answer: 'Встановіть Android-додаток або підпишіться на Telegram-канал.' },
  { icon: 'security', question: 'Наскільки це безпечно?', answer: 'Карта збирає лише публічні дані і не вимагає реєстрації.' },
  { icon: 'language', question: 'В яких регіонах працює?', answer: 'Всі 24 області та Київ — від Закарпаття до Луганщини.' },
];

export default function FaqModal({ isOpen, onClose }: FaqModalProps) {
  useEffect(() => {
    if (isOpen) document.body.style.overflow = 'hidden';
    else document.body.style.overflow = '';
    return () => { document.body.style.overflow = ''; };
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-[10000] flex items-end sm:items-center justify-center bg-black/50 backdrop-blur-md"
      onClick={onClose}
    >
      <div
        className="bg-[#1a2030] rounded-t-[28px] sm:rounded-[28px] p-5 sm:p-6 w-full sm:max-w-lg sm:w-[90%] max-h-[90vh] sm:max-h-[85vh] overflow-y-auto relative shadow-[0_8px_32px_rgba(0,0,0,0.5)]"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="w-10 h-1 bg-[#42474e] rounded-full mx-auto mb-4 sm:hidden" />

        <button
          onClick={onClose}
          className="absolute top-3 right-4 text-[#8c9099] hover:text-[#e2e2e6] active:bg-[#42474e]/40 text-2xl cursor-pointer bg-transparent border-none min-w-[44px] min-h-[44px] flex items-center justify-center rounded-xl"
        >
          &times;
        </button>

        <div className="flex items-center gap-2 mb-5">
          <span className="material-icons text-[#80d8ff]">help_outline</span>
          <h3 className="text-base sm:text-lg font-medium text-[#e2e2e6]">FAQ</h3>
        </div>

        <div className="space-y-2">
          {faqItems.map((item, i) => (
            <details key={i} className="group">
              <summary className="flex items-center gap-2.5 text-[#c2c6d0] text-[12px] sm:text-[13px] font-medium cursor-pointer list-none py-3 px-3.5 bg-[#222a3a] rounded-2xl hover:bg-[#2c3444] active:bg-[#323c50] transition-all min-h-[48px]">
                <span className="material-icons text-[16px] text-[#80d8ff]">{item.icon}</span>
                <span className="flex-1">{item.question}</span>
                <span className="material-icons text-[16px] text-[#8c9099] group-open:rotate-180 transition-transform shrink-0">
                  expand_more
                </span>
              </summary>
              <div className="text-[#8c9099] text-[11px] sm:text-[12px] leading-relaxed px-3.5 py-2.5 pl-10">
                {item.answer}
              </div>
            </details>
          ))}
        </div>

        <div className="mt-5 text-center pb-1">
          <a
            href={TELEGRAM_CHANNEL_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 text-[#80d8ff] hover:text-[#b0e0ff] text-sm transition-colors min-h-[44px]"
          >
            <span className="material-icons text-[16px]">telegram</span>
            Зв&apos;язатися в Telegram
          </a>
        </div>
      </div>
    </div>
  );
}
