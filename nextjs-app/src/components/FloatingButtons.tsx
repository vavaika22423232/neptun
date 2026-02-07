'use client';

import { GOOGLE_PLAY_URL } from '@/lib/constants';

interface FloatingButtonsProps {
  onDonate: () => void;
}

export default function FloatingButtons({ onDonate }: FloatingButtonsProps) {
  return (
    <div className="fixed bottom-6 right-6 z-[1100] flex flex-col gap-2.5 max-md:bottom-20 max-md:right-3">
      {/* Donate button */}
      <button
        onClick={onDonate}
        className="flex items-center justify-center gap-2 px-5 py-3 bg-[#2c2c2e] border border-white/10 rounded-full text-[13px] font-medium text-white/70 hover:bg-[#3a3a3c] hover:text-white transition-all cursor-pointer"
      >
        <span className="material-icons text-[20px]">favorite</span>
        <span className="btn-text">Підтримати</span>
      </button>

      {/* Google Play button */}
      <a
        href={GOOGLE_PLAY_URL}
        target="_blank"
        rel="noopener noreferrer"
        className="flex items-center justify-center gap-2 px-5 py-3 bg-[#2c2c2e] border border-white/10 rounded-full text-[13px] font-medium text-white/70 hover:bg-[#3a3a3c] hover:text-white transition-all no-underline"
      >
        <span className="material-icons text-[20px]">get_app</span>
        <span className="btn-text">Додаток</span>
      </a>
    </div>
  );
}
