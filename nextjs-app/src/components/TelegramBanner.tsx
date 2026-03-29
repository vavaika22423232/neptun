'use client';

import { TELEGRAM_CHANNEL_URL } from '@/lib/constants';

interface TelegramBannerProps {
  isCompact?: boolean;
}

export default function TelegramBanner({ isCompact }: TelegramBannerProps) {
  const baseClasses = isCompact
    ? "group relative flex items-center justify-between gap-3 px-4 py-2 bg-transparent border-t border-white/5 hover:bg-white/[0.02] transition-all cursor-pointer no-underline overflow-hidden"
    : "group fixed top-0 left-0 right-0 z-[9999] flex transform-gpu items-center justify-center gap-3 sm:gap-4 px-4 py-2.5 sm:py-2 text-white no-underline transition-all overflow-hidden border-b border-[#3A9EFD]/20 bg-[#05050f]/95 shadow-[0_4px_32px_rgba(58,158,253,0.15)] backdrop-blur-2xl hover:bg-[#050515] active:brightness-95 cursor-pointer";

  return (
    <a
      href={TELEGRAM_CHANNEL_URL}
      target="_blank"
      rel="noopener noreferrer"
      className={baseClasses}
    >
      {/* Dynamic Glare Sweep Effect */}
      <div className="pointer-events-none absolute inset-0 bg-gradient-to-r from-transparent via-[#3A9EFD]/10 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-1000 ease-in-out" />
      
      {!isCompact && (
        <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-[#3A9EFD]/40 to-transparent opacity-50" />
      )}

      <div className="flex items-center gap-2 overflow-hidden flex-1 min-w-0">
        {/* Pinging Neon Dot */}
        <span className="relative flex h-2 w-2 shrink-0">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[#3A9EFD]/80" />
          <span className="relative inline-flex h-2 w-2 rounded-full bg-[#3A9EFD] shadow-[0_0_8px_rgba(58,158,253,1)]" />
        </span>

        {/* Text Area */}
        <span className="relative z-[1] leading-tight tracking-tight flex-1 min-w-0">
          <span className="text-[9px] sm:text-[10px] text-gray-800 dark:text-[#3A9EFD]/80 font-medium">Щоб не перевіряти сайт </span>
          <strong className="font-bold text-gray-900 dark:text-white tracking-widest uppercase text-[9px] sm:text-[10px]">Хлопці пишуть в Telegram</strong>
          <span className="text-[9px] text-gray-500 dark:text-white/50 sm:text-[10px] ml-1 tracking-[0.2px]">— максимально швидко</span>
        </span>
      </div>

      {/* High-Contrast Action Button */}
      <span className={`relative z-[1] flex shrink-0 items-center justify-center gap-1.5 rounded-full border border-[#2A8AE0] dark:border-[#3A9EFD]/50 bg-[#2A8AE0] dark:bg-[#3A9EFD]/20 ${isCompact ? 'px-2.5 py-0.5' : 'px-4 py-1.5'} text-[9px] sm:text-[10px] font-bold text-white dark:text-[#e1f0ff] shadow-[0_2px_8px_rgba(42,138,224,0.3)] dark:shadow-[0_0_12px_rgba(58,158,253,0.2)] transition-all group-hover:bg-[#1E7AD0] dark:group-hover:bg-[#3A9EFD]/35 group-hover:scale-[1.03] uppercase tracking-[1px]`}>
        <svg viewBox="0 0 24 24" fill="currentColor" className="h-[12px] w-[12px] sm:h-[14px] sm:w-[14px]">
          <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 5.42-1.13 7.19-.14.75-.42 1-.68 1.03-.58.05-1.02-.38-1.58-.75-.88-.58-1.38-.94-2.23-1.5-.99-.65-.35-1.01.22-1.59.15-.15 2.71-2.48 2.76-2.69a.2.2 0 00-.05-.18c-.06-.05-.14-.03-.21-.02-.09.02-1.49.95-4.22 2.79-.4.27-.76.41-1.08.4-.36-.01-1.04-.2-1.55-.37-.63-.2-1.12-.31-1.08-.66.02-.18.27-.36.74-.55 2.92-1.27 4.86-2.11 5.83-2.51 2.78-1.16 3.35-1.36 3.73-1.36.08 0 .27.02.39.12.1.08.13.19.14.27-.01.06.01.24 0 .38z"/>
        </svg>
        <span>Підписатись!</span>
      </span>
    </a>
  );
}
