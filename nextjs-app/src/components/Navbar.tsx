'use client';

import type { PresenceData } from '@/types';

interface NavbarProps {
  presence: PresenceData;
  onDonate: () => void;
  onFaq: () => void;
}

export default function Navbar({ presence, onDonate, onFaq }: NavbarProps) {
  return (
    <nav className="navbar-safe fixed top-0 left-0 right-0 z-[1001] flex items-center justify-between px-4 py-2 max-sm:px-3 max-sm:py-1.5 bg-[#0e1218]/90 backdrop-blur-xl border-b border-[#80d8ff]/5 animate-[fadeIn_0.3s_ease-in-out_0.1s_forwards] opacity-0">
      <div className="flex items-center gap-3 max-sm:gap-2 min-w-0">
        {/* Logo with accent */}
        <span className="text-xl max-sm:text-[15px] font-semibold tracking-[5px] max-sm:tracking-[2px] bg-gradient-to-r from-[#80d8ff] to-[#b0e0ff] bg-clip-text text-transparent select-none shrink-0">
          NEPTUN
        </span>

        {/* Live indicator */}
        <div className="flex items-center gap-1.5 max-sm:gap-1 text-[11px] max-sm:text-[10px] text-[#c2c6d0]" title="Активні користувачі онлайн">
          <span className="w-1.5 h-1.5 rounded-full bg-[#69f0ae] animate-pulse" />
          <span className="font-medium text-[#e2e2e6]">{presence.total || 0}</span>
          <span className="text-[10px] max-sm:text-[9px] text-[#8c9099]">онлайн</span>
        </div>
      </div>

      <div className="flex items-center gap-1 max-sm:gap-0 shrink-0">
        <button
          onClick={onFaq}
          className="text-[#c2c6d0] hover:text-[#80d8ff] active:text-[#80d8ff] hover:bg-[#80d8ff]/8 active:bg-[#80d8ff]/12 transition-all p-2 rounded-xl min-w-[44px] min-h-[44px] flex items-center justify-center"
          aria-label="FAQ"
        >
          <span className="material-icons text-[20px]">help_outline</span>
        </button>
        <button
          onClick={onDonate}
          className="text-[#c2c6d0] hover:text-[#ff7eb3] active:text-[#ff7eb3] hover:bg-[#ff7eb3]/8 active:bg-[#ff7eb3]/12 transition-all p-2 rounded-xl min-w-[44px] min-h-[44px] flex items-center justify-center"
          aria-label="Підтримати"
        >
          <span className="material-icons text-[20px]">favorite</span>
        </button>
      </div>
    </nav>
  );
}
