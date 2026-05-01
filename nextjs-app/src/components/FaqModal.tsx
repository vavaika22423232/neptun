'use client';

import { useEffect } from 'react';
import { TELEGRAM_CHANNEL_URL } from '@/lib/constants';

interface FaqModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const faqItems = [
  { question: 'Що таке NEPTUN?', answer: 'NEPTUN — це інтерактивна радарна система моніторингу повітряних загроз в Україні в реальному часі.' },
  { question: 'Чи є карта офіційною?', answer: 'Ні, використовуйте офіційний застосунок «Повітряна тривога» для укриттів. Ми збираємо дані з публічних джерел.' },
  { question: 'Як швидко оновлюються дані?', answer: 'Затримка становить від кількох секунд до хвилини, залежно від швидкості обробки публічних радарних даних.' },
  { question: 'Мобільні додатки є?', answer: 'Так, iOS та Android версії доступні. Посилання знаходяться в нижньому доці.' },
  { question: 'Що означають стрілки і лінії?', answer: 'Це прогнозовані та поточні вектори руху цілей (балістика, дрони, авіація).' }
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
      className="fixed inset-0 z-[10000] flex items-end justify-center bg-[var(--hud-backdrop)] p-0 backdrop-blur-md transition-opacity sm:items-center sm:p-4"
      onClick={onClose}
    >
      <div
        className="relative max-h-[min(88dvh,680px)] w-full max-w-[480px] overflow-y-auto rounded-t-[28px] border border-[color:var(--hud-border)] bg-[var(--hud-surface-strong)] p-4 pb-[calc(env(safe-area-inset-bottom,0px)+1rem)] text-[var(--hud-text)] shadow-[var(--hud-modal-shadow)] backdrop-blur-xl sm:max-h-[calc(100dvh-2rem)] sm:rounded-[32px] sm:p-7"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="faq-modal-title"
      >
        <button
          onClick={onClose}
          className="absolute right-4 top-4 flex h-9 w-9 items-center justify-center rounded-full bg-[var(--hud-chip)] text-[var(--hud-muted)] transition-colors hover:bg-[var(--hud-hover)] hover:text-[var(--hud-text)] sm:right-5 sm:top-5"
          aria-label="Закрити"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
        </button>

        <div className="mb-5 pr-10 sm:mb-6">
          <p className="mb-2 text-[10px] font-black uppercase tracking-[0.32em] text-[var(--hud-danger)]">NEPTUN.IN.UA</p>
          <h3 id="faq-modal-title" className="text-[22px] font-black tracking-tight text-[var(--hud-text)] sm:text-2xl">
            База знань
          </h3>
          <p className="mt-2 max-w-[360px] text-[13px] leading-relaxed text-[var(--hud-muted)]">
            Коротко про карту, джерела даних і позначення на радарі.
          </p>
        </div>

        <div className="space-y-2.5 sm:space-y-3">
          {faqItems.map((item, i) => (
            <details key={i} className="group">
              <summary className="flex cursor-pointer items-center justify-between rounded-[18px] bg-[var(--hud-chip)] px-4 py-3.5 text-[12px] font-black uppercase tracking-[0.12em] text-[var(--hud-text)] transition-colors hover:bg-[var(--hud-hover)] list-none sm:px-5 sm:py-4">
                <span className="flex-1">{item.question}</span>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" className="ml-4 h-4 w-4 text-[var(--hud-muted)] transition-transform group-open:rotate-180"><polyline points="6 9 12 15 18 9"></polyline></svg>
              </summary>
              <div className="px-4 pb-2 pt-3 text-[13px] leading-relaxed text-[var(--hud-muted)] sm:px-5">
                {item.answer}
              </div>
            </details>
          ))}
        </div>

        <div className="mt-6 flex justify-center">
          <a
            href={TELEGRAM_CHANNEL_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="rounded-full bg-[var(--hud-text)] px-5 py-3 text-[10px] font-black uppercase tracking-[0.2em] text-[var(--hud-surface-strong)] transition-opacity hover:opacity-85"
          >
            Telegram Support
          </a>
        </div>
      </div>
    </div>
  );
}
