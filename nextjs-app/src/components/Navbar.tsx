'use client';

import type { PresenceData } from '@/types';

interface NavbarProps {
  presence: PresenceData;
  onDonate: () => void;
  onFaq: () => void;
}

export default function Navbar({ presence, onDonate, onFaq }: NavbarProps) {
  return (
    <nav className="fixed top-0 left-0 right-0 z-[1001] flex items-center justify-between px-4 py-2.5 bg-[#0a0e17]/80 backdrop-blur-md border-b border-white/5 animate-[fadeIn_0.3s_ease-in-out_0.1s_forwards] opacity-0">
      <div className="flex items-center gap-3">
        {/* Logo */}
        <span className="text-xl font-medium tracking-[6px] text-white select-none">
          NEPTUN
        </span>

        {/* Live users */}
        <div className="flex items-center gap-2 text-xs text-white/50" title="Активні користувачі онлайн">
          <span className="text-[10px] uppercase tracking-wider">онлайн</span>
          <span className="text-white/80 font-medium">{presence.total || 0}</span>
          <span className="flex gap-1.5 text-[10px]">
            <span className="flex items-center gap-0.5 bg-white/5 px-1.5 py-0.5 rounded">
              🌐<strong className="text-white/70">{presence.web || 0}</strong>
            </span>
            <span className="flex items-center gap-0.5 bg-white/5 px-1.5 py-0.5 rounded">
              📱<strong className="text-white/70">{presence.apps || 0}</strong>
            </span>
          </span>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <button
          onClick={onFaq}
          className="text-white/50 hover:text-white/80 transition-colors p-1.5"
          aria-label="FAQ"
        >
          <span className="material-icons text-[20px]">help_outline</span>
        </button>
        <button
          onClick={onDonate}
          className="text-white/50 hover:text-white/80 transition-colors p-1.5"
          aria-label="Підтримати"
        >
          <span className="material-icons text-[20px]">favorite</span>
        </button>
      </div>
    </nav>
  );
}
