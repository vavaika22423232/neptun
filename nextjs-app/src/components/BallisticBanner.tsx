'use client';

import { useState, useEffect } from 'react';
import type { BallisticThreat } from '@/types';

interface BallisticBannerProps {
  threat: BallisticThreat | null;
}

export default function BallisticBanner({ threat }: BallisticBannerProps) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    setVisible(!!threat?.active);
  }, [threat]);

  if (!visible) return null;

  return (
    <div className="fixed top-[84px] sm:top-[90px] right-2.5 sm:right-5 left-2.5 sm:left-auto bg-[#93000a] border border-[#ffb4ab]/20 rounded-2xl px-4 py-3 text-[#ffdad6] z-[9999] flex items-center gap-2.5 text-[12px] sm:text-[13px] font-medium justify-center sm:justify-start shadow-[0_4px_16px_rgba(147,0,10,0.5)] animate-[fadeIn_0.3s_ease]">
      <span className="text-base sm:text-lg">🚀</span>
      <div className="leading-snug">
        <strong className="block font-semibold text-[#ffb4ab]">Загроза балістики!</strong>
        {threat?.region && <span className="opacity-80 text-[10px] sm:text-[11px]">{threat.region}</span>}
      </div>
      <button
        onClick={() => setVisible(false)}
        className="bg-transparent border-none text-[#ffb4ab] text-lg cursor-pointer opacity-60 hover:opacity-100 p-0 ml-auto sm:ml-2 min-w-[44px] min-h-[44px] flex items-center justify-center"
        aria-label="Закрити"
      >
        &times;
      </button>
    </div>
  );
}
