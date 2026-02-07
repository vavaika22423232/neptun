'use client';

import { useState } from 'react';
import type { PresenceData } from '@/types';
import { GOOGLE_PLAY_URL, APP_STORE_URL } from '@/lib/constants';

interface NavbarProps {
  presence: PresenceData;
  onDonate: () => void;
  onFaq: () => void;
}

export default function Navbar({ presence, onDonate, onFaq }: NavbarProps) {
  const [infoOpen, setInfoOpen] = useState(false);

  return (
    <>
      <nav className="navbar-safe fixed top-0 left-0 right-0 z-[1001] flex items-center justify-between px-4 py-2 max-sm:px-3 max-sm:py-1.5 bg-[#0e1218]/90 backdrop-blur-xl border-b border-[#80d8ff]/5 animate-[fadeIn_0.3s_ease-in-out_0.1s_forwards] opacity-0">
        <div className="flex items-center gap-3 max-sm:gap-2 min-w-0">
          {/* Logo */}
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
          {/* Info */}
          <button
            onClick={() => setInfoOpen(!infoOpen)}
            className={`transition-all p-2 rounded-xl min-w-[44px] min-h-[44px] flex items-center justify-center ${infoOpen ? 'text-[#80d8ff] bg-[#80d8ff]/10' : 'text-[#c2c6d0] hover:text-[#80d8ff] hover:bg-[#80d8ff]/8 active:bg-[#80d8ff]/12'}`}
            aria-label="Інформація"
          >
            <span className="material-icons text-[20px]">info</span>
          </button>
          {/* FAQ */}
          <button
            onClick={onFaq}
            className="text-[#c2c6d0] hover:text-[#80d8ff] active:text-[#80d8ff] hover:bg-[#80d8ff]/8 active:bg-[#80d8ff]/12 transition-all p-2 rounded-xl min-w-[44px] min-h-[44px] flex items-center justify-center"
            aria-label="FAQ"
          >
            <span className="material-icons text-[20px]">help_outline</span>
          </button>
          {/* Donate */}
          <button
            onClick={onDonate}
            className="text-[#c2c6d0] hover:text-[#ff7eb3] active:text-[#ff7eb3] hover:bg-[#ff7eb3]/8 active:bg-[#ff7eb3]/12 transition-all p-2 rounded-xl min-w-[44px] min-h-[44px] flex items-center justify-center"
            aria-label="Підтримати"
          >
            <span className="material-icons text-[20px]">favorite</span>
          </button>
        </div>
      </nav>

      {/* Info panel (slides down below navbar) */}
      {infoOpen && (
        <div className="fixed top-[52px] sm:top-[58px] left-0 right-0 z-[999] bg-[#0e1218]/95 backdrop-blur-2xl border-b border-[#80d8ff]/8 shadow-[0_8px_32px_rgba(0,0,0,0.5)] max-h-[60vh] overflow-y-auto scrollbar-none animate-[fadeIn_0.15s_ease]">
          <div className="max-w-2xl mx-auto px-4 py-4 text-[#c2c6d0] text-[12px] sm:text-[13px] leading-relaxed">
            <article itemScope itemType="https://schema.org/Article">
              <meta itemProp="headline" content="Карта шахедів і тривог України онлайн" />
              <meta itemProp="author" content="NEPTUN" />

              <h2 className="text-[#e2e2e6] text-sm sm:text-base font-medium mb-2">
                Карта шахедів і тривог України — моніторинг загроз в реальному часі
              </h2>

              <p className="mb-3">
                <strong className="text-[#80d8ff]">NEPTUN</strong> — інтерактивна <strong>карта шахедів і тривог України</strong> з інформацією про <strong>повітряні тривоги</strong>, шахеди, ракети та інші загрози в реальному часі.
              </p>

              <h3 className="text-[#e2e2e6] text-[13px] sm:text-sm font-medium mt-3 mb-1.5">Що показує карта?</h3>
              <ul className="list-disc pl-5 space-y-1 mb-3 text-[#8c9099]">
                <li><strong className="text-[#c2c6d0]">Повітряна тривога</strong> — всі 25 областей України</li>
                <li><strong className="text-[#c2c6d0]">Шахеди онлайн</strong> — Shahed-136/131 з траєкторією</li>
                <li><strong className="text-[#c2c6d0]">Ракети</strong> — Х-101, Калібр, Іскандер, Кинжал</li>
                <li><strong className="text-[#c2c6d0]">КАБи</strong> — керовані авіабомби</li>
                <li><strong className="text-[#c2c6d0]">БпЛА</strong> — розвідувальні дрони</li>
              </ul>

              <h3 className="text-[#e2e2e6] text-[13px] sm:text-sm font-medium mt-3 mb-1.5">Мобільні додатки</h3>
              <div className="flex flex-wrap gap-2 mb-3">
                <a href={GOOGLE_PLAY_URL} className="inline-flex items-center gap-1.5 bg-[#69f0ae]/10 text-[#69f0ae] text-[12px] px-3 py-1.5 rounded-full hover:bg-[#69f0ae]/20 transition-colors no-underline" rel="noopener" target="_blank">
                  <span className="material-icons text-[14px]">android</span>
                  Google Play
                </a>
                <a href={APP_STORE_URL} className="inline-flex items-center gap-1.5 bg-[#80d8ff]/10 text-[#80d8ff] text-[12px] px-3 py-1.5 rounded-full hover:bg-[#80d8ff]/20 transition-colors no-underline" rel="noopener" target="_blank">
                  <span className="material-icons text-[14px]">phone_iphone</span>
                  App Store
                </a>
              </div>

              <h3 className="text-[#e2e2e6] text-[13px] sm:text-sm font-medium mt-3 mb-1.5">Переваги</h3>
              <ul className="list-disc pl-5 space-y-1 mb-3 text-[#8c9099]">
                <li>Оновлення кожні 5-10 секунд</li>
                <li>Офіційні джерела (Telegram ОВА)</li>
                <li>Push-сповіщення для Android та iOS</li>
                <li>Траєкторії шахедів та ракет</li>
                <li>Працює 24/7</li>
              </ul>

              <p className="text-[#8c9099]/50 text-[10px] mt-3">© NEPTUN 2024-2026</p>
            </article>
          </div>
        </div>
      )}
    </>
  );
}
