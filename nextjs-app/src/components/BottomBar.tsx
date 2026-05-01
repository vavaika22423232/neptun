'use client';

import { useEffect, useState, type ReactNode } from 'react';
import { TELEGRAM_CHANNEL_URL } from '@/lib/constants';

const pathTelegram =
  'M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 5.42-1.13 7.19-.14.75-.42 1-.68 1.03-.58.05-1.02-.38-1.58-.75-.88-.58-1.38-.94-2.23-1.5-.99-.65-.35-1.01.22-1.59.15-.15 2.71-2.48 2.76-2.69a.2.2 0 00-.05-.18c-.06-.05-.14-.03-.21-.02-.09.02-1.49.95-4.22 2.79-.4.27-.76.41-1.08.4-.36-.01-1.04-.2-1.55-.37-.63-.2-1.12-.31-1.08-.66.02-.18.27-.36.74-.55 2.92-1.27 4.86-2.11 5.83-2.51 2.78-1.16 3.35-1.36 3.73-1.36.08 0 .27.02.39.12.1.08.13.19.14.27-.01.06.01.24 0 .38z';

export interface BottomBarProps {
  onDonate: () => void;
  onFaq: () => void;
  onToggleUkraineOnly: () => void;
  activeAlarms: number;
  targetsCount: number;
  onlineCount: number;
  ukraineOnly: boolean;
}

function runThemeToggle() {
  const root = document.documentElement;
  const themeColor = document.querySelector('meta[name="theme-color"]');
  if (root.classList.contains('dark')) {
    root.classList.remove('dark');
    root.classList.add('theme-light');
    root.style.colorScheme = 'light';
    themeColor?.setAttribute('content', '#f5f7fa');
    localStorage.setItem('theme', 'light');
  } else {
    root.classList.remove('theme-light');
    root.classList.add('dark');
    root.style.colorScheme = 'dark';
    themeColor?.setAttribute('content', '#0a0a0b');
    localStorage.setItem('theme', 'dark');
  }
  window.dispatchEvent(new Event('theme-change'));
}

const railClassName =
  'pointer-events-auto fixed inset-x-0 bottom-0 z-[2400] flex flex-nowrap items-center justify-start gap-1.5 overflow-x-auto overscroll-x-contain border-t border-[color:var(--hud-border)] bg-[var(--hud-surface)] py-2 pl-[4.25rem] pr-2.5 pb-[calc(env(safe-area-inset-bottom,0px)+0.5rem)] text-[var(--hud-text)] shadow-[var(--hud-shadow)] backdrop-blur-xl scrollbar-none transition-colors duration-300 sm:min-h-16 sm:justify-center sm:gap-2 sm:px-3';

const quietIconButtonClassName =
  'flex h-10 w-10 shrink-0 items-center justify-center rounded-[14px] text-[var(--hud-text)] transition-colors hover:bg-[var(--hud-hover)] active:bg-[var(--hud-active)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#2563eb]/35';

const statusPillClassName =
  'flex h-10 min-w-[3.35rem] shrink-0 items-center justify-center gap-1.5 rounded-[14px] bg-[var(--hud-chip)] px-2.5 text-[12px] font-semibold tabular-nums text-[var(--hud-text)] sm:min-w-0 sm:px-3';

function IconSvg({ children, strokeWidth = 2.35 }: { children: ReactNode; strokeWidth?: number }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      className="h-5 w-5 sm:h-[22px] sm:w-[22px]"
      aria-hidden
    >
      {children}
    </svg>
  );
}

export default function BottomBar({
  onDonate,
  onFaq,
  onToggleUkraineOnly,
  activeAlarms,
  targetsCount,
  onlineCount,
  ukraineOnly,
}: BottomBarProps) {
  const [isDarkTheme, setIsDarkTheme] = useState(false);

  useEffect(() => {
    const syncTheme = () => setIsDarkTheme(document.documentElement.classList.contains('dark'));
    syncTheme();
    window.addEventListener('theme-change', syncTheme);
    return () => window.removeEventListener('theme-change', syncTheme);
  }, []);

  return (
    <nav className={railClassName} aria-label="Панель керування картою">
      <div className="hidden h-8 shrink-0 items-center gap-2 rounded-[12px] bg-[var(--hud-chip)] px-2 sm:flex sm:h-10 sm:gap-3 sm:rounded-[16px] sm:px-3">
        <span className="hidden text-[12px] font-black uppercase tracking-[0.18em] text-[var(--hud-text)] sm:block">NEPTUN</span>
        <span className="hidden h-5 w-px bg-[var(--hud-divider)] sm:block" aria-hidden />
        <span className="block h-5 w-5 overflow-hidden rounded-full shadow-[0_0_0_1px_var(--hud-border)] sm:h-6 sm:w-6" title="Україна" aria-hidden>
          <span className="block h-2.5 bg-[#198de5] sm:h-3" />
          <span className="block h-2.5 bg-[#ffd43b] sm:h-3" />
        </span>
      </div>

      <div className={statusPillClassName} title="Активні тривоги">
        <span className={`h-2 w-2 rounded-full ${activeAlarms > 0 ? 'bg-[var(--hud-danger)] shadow-[0_0_8px_rgba(143,0,0,0.7)]' : 'bg-[var(--hud-divider)]'}`} />
        <span className="hidden sm:inline">Тривоги</span>
        <span>{activeAlarms}</span>
      </div>

      <div className={statusPillClassName} title="Активні цілі">
        <IconSvg strokeWidth={2.2}>
          <circle cx="12" cy="12" r="2.5" />
          <path d="M12 4v3M12 17v3M4 12h3M17 12h3" />
        </IconSvg>
        <span className="hidden sm:inline">Цілі</span>
        <span>{targetsCount}</span>
      </div>

      <div className={statusPillClassName} title="Користувачів онлайн">
        <span className="h-2 w-2 rounded-full bg-[#16a34a] shadow-[0_0_7px_rgba(22,163,74,0.45)]" />
        <span className="hidden sm:inline">Онлайн</span>
        <span>{onlineCount}</span>
      </div>

      <div className="hidden h-8 w-px shrink-0 bg-[var(--hud-divider)] md:block" aria-hidden />

      <button type="button" title="Довідка" onClick={onFaq} className={quietIconButtonClassName} aria-label="Довідка">
        <IconSvg>
          <circle cx="12" cy="12" r="9" />
          <path d="M12 8h.01M11 12h1v5h1" />
        </IconSvg>
      </button>

      <button
        type="button"
        title={ukraineOnly ? 'Показати сусідні країни' : 'Тільки Україна'}
        onClick={(e) => {
          e.preventDefault();
          e.stopPropagation();
          onToggleUkraineOnly();
        }}
        className={`${quietIconButtonClassName} ${ukraineOnly ? 'bg-[var(--hud-hover)] text-[var(--hud-danger)]' : ''}`}
        aria-label={ukraineOnly ? 'Показати сусідні країни' : 'Показати тільки Україну'}
        aria-pressed={ukraineOnly}
      >
        <IconSvg strokeWidth={2.15}>
          <path d="M4 6.5 12 3l8 3.5v11L12 21l-8-3.5z" />
          <path d="M12 3v18M4 6.5l8 4 8-4" />
        </IconSvg>
      </button>

      <button
        type="button"
        title={isDarkTheme ? 'Світла тема' : 'Темна тема'}
        onClick={runThemeToggle}
        className={quietIconButtonClassName}
        aria-label={isDarkTheme ? 'Увімкнути світлу тему' : 'Увімкнути темну тему'}
      >
        <IconSvg>
          {isDarkTheme ? (
            <>
              <circle cx="12" cy="12" r="4" />
              <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41" />
            </>
          ) : (
            <path d="M21 12.8A8.5 8.5 0 1 1 11.2 3a6.5 6.5 0 0 0 9.8 9.8Z" />
          )}
        </IconSvg>
      </button>

      <a
        href={TELEGRAM_CHANNEL_URL}
        target="_blank"
        rel="noopener noreferrer"
        title="Telegram"
        className={quietIconButtonClassName}
        aria-label="Telegram"
      >
        <svg viewBox="0 0 24 24" className="h-[22px] w-[22px]" aria-hidden>
          <path d={pathTelegram} fill="currentColor" />
        </svg>
      </a>

      <button
        type="button"
        title="Підтримати"
        onClick={onDonate}
        className={quietIconButtonClassName}
        aria-label="Підтримати"
      >
        <IconSvg>
          <path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.6l-1-1a5.5 5.5 0 0 0-7.8 7.8l1 1L12 21l7.8-7.6 1-1a5.5 5.5 0 0 0 0-7.8Z" />
        </IconSvg>
      </button>
    </nav>
  );
}
