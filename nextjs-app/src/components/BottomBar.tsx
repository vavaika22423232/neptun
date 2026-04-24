'use client';

import { useId } from 'react';
import { APP_STORE_URL, GOOGLE_PLAY_URL, TELEGRAM_CHANNEL_URL } from '@/lib/constants';
import { withUtm } from '@/lib/share-urls';

const APP_STORE_LINK = withUtm(APP_STORE_URL, {
  source: 'neptun_site',
  medium: 'referral',
  campaign: 'bottom_bar_app_store',
});

const GOOGLE_PLAY_LINK = withUtm(GOOGLE_PLAY_URL, {
  source: 'neptun_site',
  medium: 'referral',
  campaign: 'bottom_bar_google_play',
});

/** Темна «капсула» як на референсі — однакова в світлій/темній темі сторінки. */
const shellClassName =
  'pointer-events-auto mx-auto mb-[env(safe-area-inset-bottom,1.5rem)] flex max-w-[calc(100vw-1.25rem)] touch-pan-x items-center gap-1.5 overflow-x-auto overscroll-x-contain rounded-full border border-white/[0.1] bg-[#141416]/95 p-1.5 shadow-[0_12px_40px_rgba(0,0,0,0.45)] [-ms-overflow-style:none] [scrollbar-width:none] backdrop-blur-xl md:mb-0 md:max-w-none [&::-webkit-scrollbar]:hidden';

const dividerClassName = 'mx-0.5 h-6 w-px shrink-0 bg-white/[0.12]';

/** App Store / Google Play — та сама висота, що й круглі кнопки дока (h-10). */
const storePillClassName =
  'flex h-10 min-w-0 max-w-[min(42vw,9.25rem)] shrink-0 items-center gap-1.5 rounded-full border border-white/[0.1] bg-[#1e1e22] px-2 text-left shadow-none transition-[transform,background-color] hover:bg-[#252529] active:scale-[0.98] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#ff2a5f]/35 focus-visible:ring-offset-2 focus-visible:ring-offset-[#141416] sm:max-w-[9.75rem] sm:px-2.5';

const pathApple =
  'M18.71 19.5c-.83 1.24-1.71 2.45-3.05 2.47-1.34.03-1.77-.79-3.29-.79-1.53 0-2 .77-3.27.82-1.31.05-2.3-1.32-3.14-2.53C4.25 17 2.94 12.45 4.7 9.39c.87-1.52 2.43-2.48 4.12-2.51 1.28-.02 2.5.87 3.29.87.78 0 2.26-1.07 3.8-.91.65.03 2.47.26 3.64 1.98-.09.06-2.17 1.28-2.15 3.81.03 3.02 2.65 4.03 2.68 4.04-.03.07-.42 1.44-1.38 2.83M13 3.5c.73-.83 1.94-1.46 2.94-1.5.13 1.17-.34 2.35-1.04 3.19-.69.85-1.83 1.51-2.95 1.42-.15-1.15.41-2.35 1.05-3.11z';

/** Складений шлях Google Play (як у системній іконці) — заливка градієнтом. */
const pathPlayStore =
  'M3.609 1.814L13.792 12 3.61 22.186a.996.996 0 01-.61-.92V2.734a1 1 0 01.609-.92zm10.89 10.893l2.302 2.302-10.937 6.333 8.635-8.635zm3.199-3.199l2.302 2.302-2.302 2.302-2.698-2.698 2.698-2.698-.001.792h.001v-.792zm-3.906-3.906l10.937 6.333-2.302 2.302L13.792 5.602z';

const pathTelegram =
  'M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 5.42-1.13 7.19-.14.75-.42 1-.68 1.03-.58.05-1.02-.38-1.58-.75-.88-.58-1.38-.94-2.23-1.5-.99-.65-.35-1.01.22-1.59.15-.15 2.71-2.48 2.76-2.69a.2.2 0 00-.05-.18c-.06-.05-.14-.03-.21-.02-.09.02-1.49.95-4.22 2.79-.4.27-.76.41-1.08.4-.36-.01-1.04-.2-1.55-.37-.63-.2-1.12-.31-1.08-.66.02-.18.27-.36.74-.55 2.92-1.27 4.86-2.11 5.83-2.51 2.78-1.16 3.35-1.36 3.73-1.36.08 0 .27.02.39.12.1.08.13.19.14.27-.01.06.01.24 0 .38z';

export interface BottomBarProps {
  onDonate: () => void;
  onFaq: () => void;
}

function runThemeToggle() {
  const root = document.documentElement;
  if (root.classList.contains('dark')) {
    root.classList.remove('dark');
    root.classList.add('theme-light');
    localStorage.setItem('theme', 'light');
  } else {
    root.classList.remove('theme-light');
    root.classList.add('dark');
    localStorage.setItem('theme', 'dark');
  }
  window.dispatchEvent(new Event('theme-change'));
}

/**
 * Нижня панель: зовнішня «пігулка» + внутрішні вузли як у копії DOM / DevTools.
 * @param props — кнопки донату та FAQ
 */
function GooglePlayIcon({ gradientId }: { gradientId: string }) {
  return (
    <svg viewBox="0 0 24 24" className="h-5 w-5 shrink-0" aria-hidden>
      <defs>
        <linearGradient id={gradientId} x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#00D9FF" />
          <stop offset="35%" stopColor="#00F076" />
          <stop offset="65%" stopColor="#FFD23B" />
          <stop offset="100%" stopColor="#FF3A44" />
        </linearGradient>
      </defs>
      <path fill={`url(#${gradientId})`} d={pathPlayStore} />
    </svg>
  );
}

export default function BottomBar({ onDonate, onFaq }: BottomBarProps) {
  const playGradId = useId().replace(/:/g, '');

  return (
    <div className={shellClassName}>
      <button
        type="button"
        title="Системний Лог"
        onClick={() => window.dispatchEvent(new CustomEvent('toggle-system-log'))}
        className="flex h-10 shrink-0 items-center rounded-full border border-[#c41e3a]/55 bg-transparent px-3.5 text-[11px] font-semibold lowercase tracking-wide text-[#ff3b5c] transition-colors hover:border-[#ff2a5f]/80 hover:bg-[#ff2a5f]/08"
        aria-label="Системний лог"
      >
        <span className="whitespace-nowrap">сис. лог</span>
      </button>

      <div className={dividerClassName} aria-hidden />

      <button
        type="button"
        title="Тема (Світла/Темна)"
        onClick={runThemeToggle}
        className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-white/[0.08] bg-white/[0.06] text-white/85 transition-colors hover:bg-white/[0.12]"
        aria-label="Тема (світла/темна)"
      >
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="h-[18px] w-[18px] opacity-90 transition-transform hover:scale-105 active:scale-95 dark:hidden"
          aria-hidden
        >
          <path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z" />
        </svg>
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="hidden h-[18px] w-[18px] opacity-90 transition-transform hover:scale-105 active:scale-95 dark:block"
          aria-hidden
        >
          <circle cx="12" cy="12" r="4" />
          <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41" />
        </svg>
      </button>

      <a
        href={TELEGRAM_CHANNEL_URL}
        target="_blank"
        rel="noopener noreferrer"
        title="Telegram"
        className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-white/[0.08] bg-white/[0.06] text-white/85 transition-colors hover:bg-white/[0.12]"
        aria-label="Telegram"
      >
        <svg viewBox="0 0 24 24" className="h-4 w-4 opacity-90" aria-hidden>
          <path d={pathTelegram} fill="currentColor" />
        </svg>
      </a>

      <a
        href={APP_STORE_LINK}
        target="_blank"
        rel="noopener noreferrer"
        aria-label="Завантажити NEPTUN у App Store"
        title="App Store — NEPTUN"
        className={storePillClassName}
      >
        <svg viewBox="0 0 24 24" className="h-5 w-5 shrink-0 text-white" aria-hidden>
          <path d={pathApple} fill="currentColor" />
        </svg>
        <span className="flex min-w-0 flex-1 flex-col justify-center gap-px text-left leading-tight">
          <span className="truncate text-[11.5px] font-semibold text-white sm:text-[12px]">App Store</span>
          <span className="text-[8px] font-medium uppercase tracking-[0.12em] text-white/45">Завантажити</span>
        </span>
      </a>

      <a
        href={GOOGLE_PLAY_LINK}
        target="_blank"
        rel="noopener noreferrer"
        aria-label="Завантажити NEPTUN у Google Play"
        title="Google Play — NEPTUN"
        className={storePillClassName}
      >
        <GooglePlayIcon gradientId={`gp-${playGradId}`} />
        <span className="flex min-w-0 flex-1 flex-col justify-center gap-px text-left leading-tight">
          <span className="truncate text-[11.5px] font-semibold text-white sm:text-[12px]">Google Play</span>
          <span className="text-[8px] font-medium uppercase tracking-[0.12em] text-white/45">Завантажити</span>
        </span>
      </a>

      <div className={dividerClassName} aria-hidden />

      <button
        type="button"
        title="Підтримати"
        onClick={onDonate}
        className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-[#ff2a5f]/20 bg-[#ff2a5f]/12 text-[#ff7a96] transition-colors hover:border-[#ff2a5f]/35 hover:bg-[#ff2a5f]/18"
        aria-label="Підтримати"
      >
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="h-[18px] w-[18px]"
          aria-hidden
        >
          <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" />
        </svg>
      </button>

      <button
        type="button"
        title="Довідка"
        onClick={onFaq}
        className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-white/[0.08] bg-white/[0.06] text-white/70 transition-colors hover:bg-white/[0.12] hover:text-white/90"
        aria-label="Довідка"
      >
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="h-4 w-4"
          aria-hidden
        >
          <circle cx="12" cy="12" r="10" />
          <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />
          <line x1="12" y1="17" x2="12.01" y2="17" />
        </svg>
      </button>
    </div>
  );
}
