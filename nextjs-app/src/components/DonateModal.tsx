'use client';

import { useState, useEffect } from 'react';
import { COME_BACK_ALIVE_DONATE_URL, UNITED24_DONATE_URL } from '@/lib/constants';

interface DonateModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function DonateModal({ isOpen, onClose }: DonateModalProps) {
  const [toast, setToast] = useState(false);

  useEffect(() => {
    if (isOpen) document.body.style.overflow = 'hidden';
    else document.body.style.overflow = '';
    return () => { document.body.style.overflow = ''; };
  }, [isOpen]);

  if (!isOpen) return null;

  const copyDonate = (text: string) => {
    navigator.clipboard.writeText(text);
    setToast(true);
    setTimeout(() => setToast(false), 2000);
  };

  const openJar = () => {
    window.open('https://send.monobank.ua/jar/6Vi9TVzJZQ', '_blank');
  };

  const openOfficialDonation = (url: string) => {
    window.open(url, '_blank', 'noopener,noreferrer');
  };

  return (
    <>
      <div
        className="fixed inset-0 z-[10000] flex items-end justify-center bg-[var(--hud-backdrop)] p-0 backdrop-blur-md transition-opacity sm:items-center sm:p-4"
        onClick={onClose}
      >
        <div
          className="relative max-h-[min(88dvh,680px)] w-full max-w-[440px] overflow-y-auto rounded-t-[28px] border border-[color:var(--hud-border)] bg-[var(--hud-surface-strong)] p-4 pb-[calc(env(safe-area-inset-bottom,0px)+1rem)] text-[var(--hud-text)] shadow-[var(--hud-modal-shadow)] backdrop-blur-xl sm:max-h-[calc(100dvh-2rem)] sm:rounded-[32px] sm:p-7"
          onClick={(e) => e.stopPropagation()}
          role="dialog"
          aria-modal="true"
          aria-labelledby="donate-modal-title"
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
            <h3 id="donate-modal-title" className="text-[22px] font-black tracking-tight text-[var(--hud-text)] sm:text-2xl">
              Підтримка NEPTUN
            </h3>
            <p className="mt-2 max-w-[360px] text-[13px] leading-relaxed text-[var(--hud-muted)]">
              Сервери, радарні інтеграції та підтримка додатків вимагають ресурсів. Допоможіть нам працювати швидше.
            </p>
          </div>

          <div className="space-y-2.5 relative z-10 sm:space-y-3">
            <div className="flex items-center justify-between gap-4 rounded-[20px] bg-[var(--hud-chip)] p-4 sm:p-5">
              <div>
                <div className="mb-1 text-[10px] font-black uppercase tracking-[0.2em] text-[var(--hud-danger)]">United24</div>
                <div className="text-[14px] font-bold text-[var(--hud-text)]">Офіційна платформа України</div>
              </div>
              <button
                onClick={() => openOfficialDonation(UNITED24_DONATE_URL)}
                className="flex shrink-0 items-center gap-2 rounded-[14px] bg-[var(--hud-text)] px-4 py-2.5 text-[10px] font-black uppercase tracking-[0.16em] text-[var(--hud-surface-strong)] transition-opacity hover:opacity-85"
              >
                Відкрити
              </button>
            </div>

            <div className="flex items-center justify-between gap-4 rounded-[20px] bg-[var(--hud-chip)] p-4 sm:p-5">
              <div>
                <div className="mb-1 text-[10px] font-black uppercase tracking-[0.2em] text-[var(--hud-danger)]">Повернись живим</div>
                <div className="text-[14px] font-bold text-[var(--hud-text)]">Допомога Силам оборони</div>
              </div>
              <button
                onClick={() => openOfficialDonation(COME_BACK_ALIVE_DONATE_URL)}
                className="flex shrink-0 items-center gap-2 rounded-[14px] bg-[var(--hud-text)] px-4 py-2.5 text-[10px] font-black uppercase tracking-[0.16em] text-[var(--hud-surface-strong)] transition-opacity hover:opacity-85"
              >
                Відкрити
              </button>
            </div>

            <div className="flex items-center justify-between gap-4 rounded-[20px] bg-[var(--hud-chip)] p-4 sm:p-5">
              <div>
                <div className="mb-1 text-[10px] font-black uppercase tracking-[0.2em] text-[var(--hud-danger)]">Monobank Jar</div>
                <div className="text-[14px] font-bold text-[var(--hud-text)]">Банка NEPTUN</div>
              </div>
              <button
                onClick={openJar}
                className="flex shrink-0 items-center gap-2 rounded-[14px] bg-[var(--hud-text)] px-4 py-2.5 text-[10px] font-black uppercase tracking-[0.16em] text-[var(--hud-surface-strong)] transition-opacity hover:opacity-85"
              >
                Відкрити
              </button>
            </div>

            <div className="flex items-center justify-between gap-4 rounded-[20px] bg-[var(--hud-chip)] p-4 sm:p-5">
              <div className="min-w-0">
                <div className="mb-1 text-[10px] font-black uppercase tracking-[0.2em] text-[var(--hud-muted)]">Mono (UAH)</div>
                <div className="break-all font-mono text-[14px] font-semibold tracking-wide text-[var(--hud-text)] sm:text-[16px]">4441 1111 2110 7290</div>
              </div>
              <button
                onClick={() => copyDonate('4441111121107290')}
                className="flex h-10 w-10 shrink-0 items-center justify-center rounded-[14px] bg-[var(--hud-hover)] text-[var(--hud-text)] transition-colors hover:bg-[var(--hud-active)]"
                aria-label="Скопіювати Mono"
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
              </button>
            </div>

            <div className="flex items-center justify-between gap-4 rounded-[20px] bg-[var(--hud-chip)] p-4 sm:p-5">
              <div className="min-w-0">
                <div className="mb-1 text-[10px] font-black uppercase tracking-[0.2em] text-[var(--hud-muted)]">Приват (UAH)</div>
                <div className="break-all font-mono text-[14px] font-semibold tracking-wide text-[var(--hud-text)] sm:text-[16px]">5168 7451 5313 3886</div>
              </div>
              <button
                onClick={() => copyDonate('5168745153133886')}
                className="flex h-10 w-10 shrink-0 items-center justify-center rounded-[14px] bg-[var(--hud-hover)] text-[var(--hud-text)] transition-colors hover:bg-[var(--hud-active)]"
                aria-label="Скопіювати Приват"
              >
                 <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
              </button>
            </div>
          </div>
        </div>
      </div>

      {toast && (
        <div className="fixed bottom-12 left-1/2 z-[10001] -translate-x-1/2 rounded-full bg-[var(--hud-text)] px-6 py-3 text-[11px] font-black uppercase tracking-[0.18em] text-[var(--hud-surface-strong)] shadow-[var(--hud-modal-shadow)] pointer-events-none">
          Скопійовано
        </div>
      )}
    </>
  );
}
