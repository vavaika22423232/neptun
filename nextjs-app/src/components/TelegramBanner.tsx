'use client';

import { TELEGRAM_CHANNEL_URL } from '@/lib/constants';

export default function TelegramBanner() {
  return (
    <a
      href={TELEGRAM_CHANNEL_URL}
      target="_blank"
      rel="noopener noreferrer"
      className="fixed top-[52px] sm:top-[58px] left-0 right-0 z-[1000] flex items-center justify-center gap-3 sm:gap-4 bg-gradient-to-r from-[#0088cc] via-[#0099dd] to-[#00aaee] px-4 py-2.5 sm:py-2 text-white no-underline hover:brightness-110 active:brightness-90 transition-all shadow-[0_2px_12px_rgba(0,136,204,0.4)]"
    >
      {/* Pulse dot */}
      <span className="relative flex h-2.5 w-2.5 shrink-0">
        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-white/60" />
        <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-white" />
      </span>

      {/* Text */}
      <span className="text-[11px] sm:text-[13px] leading-tight text-center sm:text-left">
        <span className="opacity-75 text-[10px] sm:text-[11px] block sm:inline">Щоб не перевіряти сайт </span>
        <strong className="font-bold">Хлопці пишуть в Telegram</strong>
        <span className="opacity-60 text-[10px] sm:text-[11px] hidden sm:inline"> — тривоги та рух дронів максимально швидко</span>
      </span>

      {/* CTA pill */}
      <span className="shrink-0 bg-white/20 backdrop-blur-sm rounded-full px-3 py-1 text-[11px] sm:text-[12px] font-bold flex items-center gap-1 border border-white/20 hover:bg-white/30 transition-colors">
        Підписатися
        <svg viewBox="0 0 24 24" fill="currentColor" className="w-3.5 h-3.5">
          <path d="M12 4l-1.41 1.41L16.17 11H4v2h12.17l-5.58 5.59L12 20l8-8z" />
        </svg>
      </span>
    </a>
  );
}
