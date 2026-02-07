'use client';

import { useState } from 'react';
import { TELEGRAM_CHANNEL_URL, GOOGLE_PLAY_URL } from '@/lib/constants';

interface BottomBarProps {
  onDonate: () => void;
  onFaq: () => void;
}

export default function BottomBar({ onDonate, onFaq }: BottomBarProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div
      className={`fixed bottom-4 left-1/2 -translate-x-1/2 z-[1200] bg-[#1c1c1e]/95 backdrop-blur-xl border border-white/8 rounded-2xl px-3 py-2 transition-all duration-300 ${
        expanded ? 'w-[calc(100%-32px)] max-w-2xl' : 'w-auto'
      }`}
    >
      <div className="flex items-center gap-1 justify-center">
        {/* Brand */}
        <span className="text-white/30 text-[10px] font-medium tracking-wider mr-2 max-sm:hidden">
          NEPTUN
        </span>

        {/* Telegram */}
        <a
          href={TELEGRAM_CHANNEL_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1 px-3 py-2 rounded-xl text-white/50 hover:bg-white/5 hover:text-[#2AABEE] transition-colors no-underline text-[10px]"
        >
          <span className="material-icons text-[18px]">telegram</span>
          <span>Telegram</span>
        </a>

        {/* App */}
        <a
          href={GOOGLE_PLAY_URL}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1 px-3 py-2 rounded-xl text-white/50 hover:bg-white/5 hover:text-green-400 transition-colors no-underline text-[10px]"
        >
          <span className="material-icons text-[18px]">get_app</span>
          <span>Додаток</span>
        </a>

        {/* FAQ */}
        <button
          onClick={onFaq}
          className="flex items-center gap-1 px-3 py-2 rounded-xl text-white/50 hover:bg-white/5 hover:text-blue-400 transition-colors text-[10px] bg-transparent border-none cursor-pointer"
        >
          <span className="material-icons text-[18px]">help_outline</span>
          <span>FAQ</span>
        </button>

        {/* Donate */}
        <button
          onClick={onDonate}
          className="flex items-center gap-1 px-3 py-2 rounded-xl text-white/50 hover:bg-white/5 hover:text-pink-400 transition-colors text-[10px] bg-transparent border-none cursor-pointer"
        >
          <span className="material-icons text-[18px]">favorite</span>
          <span>Підтримати</span>
        </button>

        {/* SEO toggle */}
        <button
          onClick={() => setExpanded(!expanded)}
          className={`flex items-center gap-1 px-3 py-2 rounded-xl text-white/50 hover:bg-white/5 transition-colors text-[10px] bg-transparent border-none cursor-pointer ${
            expanded ? 'bg-white/10 text-white' : ''
          }`}
        >
          <span className="material-icons text-[18px]">info</span>
          <span>Інфо</span>
        </button>
      </div>

      {/* SEO expandable content */}
      {expanded && (
        <div className="mt-2.5 pt-2.5 border-t border-white/8 max-h-[50vh] overflow-y-auto text-white/50 text-[13px] leading-relaxed px-3 pb-3">
          <h2 className="text-white text-base font-medium mb-2">
            Карта шахедів і тривог України
          </h2>
          <p className="mb-3">
            <strong className="text-white">NEPTUN</strong> — це сучасна інтерактивна карта шахедів і тривог України,
            яка відображає актуальну інформацію про повітряні тривоги, шахеди, ракети та інші загрози
            в режимі реального часу.
          </p>
          <h3 className="text-white/80 text-sm font-medium mb-1.5">Що показує карта?</h3>
          <ul className="list-disc pl-5 space-y-1 mb-3">
            <li>Повітряна тривога — активні сирени по всіх 25 областях України</li>
            <li>Шахеди онлайн — відстеження дронів-камікадзе Shahed з траєкторією</li>
            <li>Крилаті ракети — моніторинг Х-101, Калібр з прогнозом</li>
            <li>Балістичні ракети — Іскандер, Кинжал</li>
            <li>БпЛА розвідники — Орлан, Supercam</li>
          </ul>
        </div>
      )}
    </div>
  );
}
