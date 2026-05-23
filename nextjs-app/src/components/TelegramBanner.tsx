'use client';

import { TELEGRAM_CHANNEL_URL } from '@/lib/constants';

const TELEGRAM_PLANE_PATH =
  'M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 5.42-1.13 7.19-.14.75-.42 1-.68 1.03-.58.05-1.02-.38-1.58-.75-.88-.58-1.38-.94-2.23-1.5-.99-.65-.35-1.01.22-1.59.15-.15 2.71-2.48 2.76-2.69a.2.2 0 00-.05-.18c-.06-.05-.14-.03-.21-.02-.09.02-1.49.95-4.22 2.79-.4.27-.76.41-1.08.4-.36-.01-1.04-.2-1.55-.37-.63-.2-1.12-.31-1.08-.66.02-.18.27-.36.74-.55 2.92-1.27 4.86-2.11 5.83-2.51 2.78-1.16 3.35-1.36 3.73-1.36.08 0 .27.02.39.12.1.08.13.19.14.27-.01.06.01.24 0 .38z';

interface TelegramBannerProps {
  className?: string;
}

export default function TelegramBanner({ className = '' }: TelegramBannerProps) {
  return (
    <a
      href={TELEGRAM_CHANNEL_URL}
      target="_blank"
      rel="noopener noreferrer"
      aria-label="Telegram-канал NEPTUN — підписатись"
      title="Telegram-канал NEPTUN"
      className={`hud-top-pill cinematic-button group${className ? ` ${className}` : ''}`}
    >
      <span
        className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-[var(--hud-chip)] text-[#2aabee]"
        aria-hidden
      >
        <svg viewBox="0 0 24 24" className="h-[17px] w-[17px]" fill="currentColor">
          <path d={TELEGRAM_PLANE_PATH} />
        </svg>
      </span>

      <span className="flex min-w-0 flex-1 flex-col justify-center gap-px leading-tight">
        <span className="truncate text-[10px] font-medium text-[var(--hud-muted)]">
          Щоб не перевіряти сайт
        </span>
        <span className="truncate text-[10px] font-bold uppercase tracking-[0.04em] text-[var(--hud-text)]">
          Хлопці пишуть у Telegram
        </span>
      </span>

      <span className="shrink-0 rounded-full border border-[color:var(--hud-border)] bg-[var(--hud-chip)] px-2 py-1 text-[9px] font-bold uppercase tracking-[0.08em] text-[var(--hud-text)] transition-colors group-hover:bg-[var(--hud-hover)]">
        Підписатись
      </span>
    </a>
  );
}
