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
    <div className="fixed top-[90px] right-5 bg-red-500 rounded-xl px-4 py-3 text-white z-[9999] flex items-center gap-2.5 text-[13px] font-medium max-md:top-[70px] max-md:right-2.5 max-md:left-2.5 max-md:justify-center animate-[fadeIn_0.3s_ease]">
      <span className="text-lg">🚀</span>
      <div className="leading-snug">
        <strong className="block font-semibold">Загроза балістики!</strong>
        {threat?.region && <span className="opacity-80 text-[11px]">{threat.region}</span>}
      </div>
      <button
        onClick={() => setVisible(false)}
        className="bg-transparent border-none text-white text-lg cursor-pointer opacity-60 hover:opacity-100 p-0 ml-2"
        aria-label="Закрити"
      >
        &times;
      </button>
    </div>
  );
}
