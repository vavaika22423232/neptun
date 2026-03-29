'use client';

import { useState, useEffect } from 'react';

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

  return (
    <>
      <div
        className="fixed inset-0 z-[10000] flex items-center justify-center p-4 bg-[#050505]/80 backdrop-blur-md opacity-100 transition-opacity"
        onClick={onClose}
      >
        <div
          className="relative w-full max-w-[440px] bg-[#0a0a0b]/80 backdrop-blur-[64px] border border-white/[0.08] shadow-[0_32px_64px_rgba(0,0,0,0.8),inset_0_1px_0_rgba(255,255,255,0.06)] rounded-[32px] p-8 overflow-hidden"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="pointer-events-none absolute -top-24 -right-24 w-48 h-48 bg-[#ff2a5f]/20 blur-[64px] rounded-full" />
          
          <button
            onClick={onClose}
            className="absolute right-6 top-6 w-8 h-8 flex items-center justify-center rounded-full bg-white/5 hover:bg-[#ff2a5f]/20 hover:text-[#ff2a5f] text-white/50 transition-colors"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
          </button>

          <h3 className="text-sm font-bold tracking-[0.2em] uppercase text-[#ff2a5f] mb-2 flex items-center gap-2">
            Підтримка NEPTUN
          </h3>
          <p className="text-[12px] font-medium text-white/50 mb-8">
            Сервери, радарні інтеграції та підтримка додатків вимагають ресурсів. Допоможіть нам працювати швидше.
          </p>

          <div className="space-y-3 relative z-10">
            <div className="flex items-center justify-between rounded-2xl bg-white/5 p-5">
              <div>
                <div className="text-[10px] font-bold tracking-widest text-white/40 uppercase mb-1">Monobank Jar</div>
                <div className="text-[14px] font-semibold text-white">Банка NEPTUN</div>
              </div>
              <button
                onClick={openJar}
                className="flex items-center gap-2 bg-[#ff2a5f]/20 hover:bg-[#ff2a5f]/30 text-[#ff2a5f] px-4 py-2 rounded-xl text-[11px] font-bold uppercase tracking-widest transition-colors"
              >
                Відкрити
              </button>
            </div>

            <div className="flex items-center justify-between rounded-2xl bg-white/5 p-5">
              <div>
                <div className="text-[10px] font-bold tracking-widest text-[#fbbf24] uppercase mb-1">Mono (UAH)</div>
                <div className="text-[16px] font-mono tracking-wider text-white">4441 1111 2110 7290</div>
              </div>
              <button
                onClick={() => copyDonate('4441111121107290')}
                className="w-10 h-10 flex items-center justify-center rounded-xl bg-white/10 hover:bg-white/20 text-white transition-colors"
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
              </button>
            </div>

            <div className="flex items-center justify-between rounded-2xl bg-white/5 p-5">
              <div>
                <div className="text-[10px] font-bold tracking-widest text-white/40 uppercase mb-1">Приват (UAH)</div>
                <div className="text-[16px] font-mono tracking-wider text-white">5168 7451 5313 3886</div>
              </div>
              <button
                onClick={() => copyDonate('5168745153133886')}
                className="w-10 h-10 flex items-center justify-center rounded-xl bg-white/10 hover:bg-white/20 text-white transition-colors"
              >
                 <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
              </button>
            </div>
          </div>
        </div>
      </div>

      {toast && (
        <div className="fixed bottom-12 left-1/2 -translate-x-1/2 z-[10001] bg-[#69f0ae] text-[#003322] text-[11px] uppercase tracking-widest font-bold px-6 py-3 rounded-full shadow-[0_4px_24px_rgba(105,240,174,0.4)] pointer-events-none">
          Скопійовано
        </div>
      )}
    </>
  );
}
