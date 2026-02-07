'use client';

import { TELEGRAM_CHANNEL_URL, GOOGLE_PLAY_URL, APP_STORE_URL } from '@/lib/constants';

export default function BottomBar() {
  return (
    <div className="bottom-safe fixed bottom-3 sm:bottom-4 left-1/2 -translate-x-1/2 z-[1200] bg-[#1a2030]/95 backdrop-blur-2xl border border-[#80d8ff]/8 rounded-[20px] transition-all duration-300 shadow-[0_4px_24px_rgba(0,0,0,0.4)] w-auto px-2 sm:px-3 py-1.5 sm:py-2">
      <div className="flex items-center gap-0 sm:gap-0.5 justify-center">
        {/* Telegram */}
        <a
          href={TELEGRAM_CHANNEL_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="flex flex-col items-center gap-0.5 px-3 sm:px-4 py-1.5 rounded-2xl text-[#c2c6d0] hover:bg-[#80d8ff]/8 active:bg-[#80d8ff]/12 hover:text-[#2AABEE] transition-all no-underline min-h-[48px] justify-center"
        >
          <span className="material-icons text-[20px]">telegram</span>
          <span className="text-[9px] sm:text-[10px]">Telegram</span>
        </a>

        {/* Android */}
        <a
          href={GOOGLE_PLAY_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="flex flex-col items-center gap-0.5 px-2.5 sm:px-3 py-1.5 rounded-2xl text-[#c2c6d0] hover:bg-[#69f0ae]/8 active:bg-[#69f0ae]/12 hover:text-[#69f0ae] transition-all no-underline min-h-[48px] justify-center"
          aria-label="Завантажити з Google Play"
        >
          <span className="material-icons text-[20px]">android</span>
          <span className="text-[9px] sm:text-[10px]">Android</span>
        </a>

        {/* iOS */}
        <a
          href={APP_STORE_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="flex flex-col items-center gap-0.5 px-2.5 sm:px-3 py-1.5 rounded-2xl text-[#c2c6d0] hover:bg-[#80d8ff]/8 active:bg-[#80d8ff]/12 hover:text-white transition-all no-underline min-h-[48px] justify-center"
          aria-label="Завантажити з App Store"
        >
          <span className="material-icons text-[20px]">phone_iphone</span>
          <span className="text-[9px] sm:text-[10px]">iOS</span>
        </a>
      </div>
    </div>
  );
}
