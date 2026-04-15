'use client';

import { useEffect } from 'react';
import { APP_STORE_URL, GOOGLE_PLAY_URL, TELEGRAM_CHANNEL_URL } from '@/lib/constants';

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
      className="fixed inset-0 z-[10000] flex items-center justify-center p-4 bg-[#050505]/80 backdrop-blur-md opacity-100 transition-opacity"
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-[480px] bg-[#0a0a0b]/80 backdrop-blur-xl border border-white/[0.08] shadow-[0_32px_64px_rgba(0,0,0,0.8),inset_0_1px_0_rgba(255,255,255,0.06)] rounded-[32px] p-8 overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          onClick={onClose}
          className="absolute right-6 top-6 w-8 h-8 flex items-center justify-center rounded-full bg-white/5 hover:bg-[#ff2a5f]/20 hover:text-[#ff2a5f] text-white/50 transition-colors"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
        </button>

        <h3 className="text-sm font-bold tracking-[0.2em] uppercase text-white mb-8">
          База Знань
        </h3>

        <div className="space-y-3">
          {faqItems.map((item, i) => (
            <details key={i} className="group">
              <summary className="flex cursor-pointer items-center justify-between rounded-2xl bg-white/5 hover:bg-white/10 px-5 py-4 text-[12px] font-bold tracking-widest text-white/80 uppercase transition-colors list-none">
                <span className="flex-1">{item.question}</span>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4 text-white/40 transition-transform group-open:rotate-180"><polyline points="6 9 12 15 18 9"></polyline></svg>
              </summary>
              <div className="px-5 py-4 text-[13px] leading-relaxed text-white/60">
                {item.answer}
              </div>
            </details>
          ))}
        </div>

        <div className="mt-8 flex justify-center gap-4">
          <a href={TELEGRAM_CHANNEL_URL} target="_blank" className="text-[10px] font-bold uppercase tracking-widest text-[#69f0ae] hover:text-[#69f0ae]/80 transition-colors">Telegram Support</a>
        </div>
      </div>
    </div>
  );
}
