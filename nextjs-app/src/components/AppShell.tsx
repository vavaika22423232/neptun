'use client';

import React, { useState } from 'react';
import type { Marker, Alarm, BallisticThreat, PresenceData } from '@/types';
import ThreatFeed from './ThreatFeed';
import { TELEGRAM_CHANNEL_URL, APP_STORE_URL, GOOGLE_PLAY_URL } from '@/lib/constants';
import TelegramBanner from './TelegramBanner';

interface AppShellProps {
  markers: Marker[];
  alarms: Alarm[];
  presence: PresenceData;
  ballisticThreat: BallisticThreat | null;
  onDonate: () => void;
  onFaq: () => void;
  children: React.ReactNode;
}

export default function AppShell({ markers, alarms, presence, ballisticThreat, onDonate, onFaq, children }: AppShellProps) {
  const [expanded, setExpanded] = useState(false);
  const activeAlarms = alarms.filter(a => a.activeAlerts?.length > 0).length;
  const hasThreats = markers.length > 0 || alarms.some(a => a.activeAlerts?.length > 0);

  return (
    <div className="relative h-[100dvh] w-full overflow-hidden text-gray-900 dark:text-white font-sans selection:bg-[#ff2a5f]/30 transition-colors duration-300">
      
      {/* 100% Immersive Map Background */}
      <main className="absolute inset-0 z-0">
        {children}
      </main>

      {/* Floating HUD Layer */}
      <div className="pointer-events-none absolute inset-0 z-[2000] flex flex-col items-center justify-between p-6 pb-20 md:p-8">
        
        {/* Top Control Center (Bento Capsule) */}
        <div className="relative w-full max-w-[420px]">
          
          {/* Main Capsule */}
          <div 
            className={`pointer-events-auto flex flex-col overflow-hidden transition-all duration-500 will-change-transform ease-[cubic-bezier(0.16,1,0.3,1)]
              bg-white/90 border border-gray-200/50 shadow-[0_12px_48px_rgba(0,0,0,0.1),inset_0_1px_0_rgba(255,255,255,0.5)] 
              dark:bg-[#0a0a0b]/80 dark:border-white/[0.08] dark:shadow-[0_24px_64px_rgba(0,0,0,0.6),inset_0_1px_0_rgba(255,255,255,0.06)] 
              backdrop-blur-[64px]
              ${expanded ? 'rounded-[32px] h-[580px] md:h-[640px]' : 'rounded-[28px] h-[110px]'}
            `}
          >
            {/* Capsule Header (Always Visible) */}
            <div className="flex flex-col shrink-0">
              <div 
                className="h-[54px] px-6 flex items-center justify-between cursor-pointer"
                onClick={() => setExpanded(!expanded)}
              >
                <span className="text-sm font-bold tracking-[0.2em] uppercase text-gray-900 dark:text-white">NEPTUN</span>
                
                <div className="flex items-center gap-3 sm:gap-4">
                  <div className="flex items-center gap-1.5">
                    <span className={`h-1.5 w-1.5 rounded-full ${activeAlarms > 0 ? 'bg-[#ff2a5f] animate-pulse shadow-[0_0_8px_#ff2a5f]' : 'bg-black/20 dark:bg-white/20'}`} />
                    <span className="text-[11px] sm:text-[12px] font-medium text-gray-700 dark:text-white/80 tabular-nums">Тривоги: {activeAlarms}</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span className={`h-1.5 w-1.5 rounded-full ${markers.length > 0 ? 'bg-[#fbbf24] animate-pulse shadow-[0_0_8px_#fbbf24]' : 'bg-black/20 dark:bg-white/20'}`} />
                    <span className="text-[11px] sm:text-[12px] font-medium text-gray-700 dark:text-white/80 tabular-nums">Цілі: {markers.length}</span>
                  </div>
                  <div className="flex items-center gap-1.5 opacity-60 dark:opacity-50" title="Користувачів онлайн">
                    <span className="h-1.5 w-1.5 rounded-full bg-[#10b981] dark:bg-[#69f0ae] shadow-[0_0_6px_#10b981] dark:shadow-[0_0_6px_#69f0ae]" />
                    <svg className="w-3 h-3 text-gray-800 dark:text-white" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>
                    <span className="text-[11px] sm:text-[12px] font-medium tabular-nums text-gray-800 dark:text-white">{presence.total}</span>
                  </div>
                </div>
              </div>

              {/* Integrated Telegram Row */}
              <TelegramBanner isCompact />
            </div>

            {/* Expanded Content (Bento Feed) */}
            <div 
              className={`flex-1 overflow-y-auto scrollbar-none px-6 pb-6 pt-2 transition-opacity duration-300
                ${expanded ? 'opacity-100 delay-200' : 'opacity-0 pointer-events-none'}
              `}
            >
              {hasThreats ? (
                <ThreatFeed markers={markers} alarms={alarms} ballisticThreat={ballisticThreat} />
              ) : (
                <div className="h-full flex flex-col items-center justify-center opacity-40">
                  <svg className="w-12 h-12 mb-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"></circle><path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"></path><path d="M2 12h20"></path></svg>
                  <span className="text-[11px] font-bold tracking-[0.2em] uppercase">Радар Чистий</span>
                </div>
              )}
            </div>
          </div>

        </div>

        {/* Bottom Spatial Dock */}
        <div className="pointer-events-auto flex items-center gap-2 p-2 bg-white/60 dark:bg-[#0a0a0b]/40 backdrop-blur-[64px] border border-gray-200/60 dark:border-white/[0.08] shadow-[0_8px_24px_rgba(0,0,0,0.1)] dark:shadow-[0_16px_32px_rgba(0,0,0,0.5)] rounded-full mb-[env(safe-area-inset-bottom,1.5rem)] md:mb-0 transition-colors duration-300">
          <button onClick={() => window.dispatchEvent(new CustomEvent('toggle-system-log'))} title="Системний Лог" className="h-10 px-4 flex items-center gap-2 rounded-full border border-[#ff2a5f]/30 bg-red-50 dark:bg-[#050505]/90 text-[11px] text-[#ff2a5f] dark:text-[#ff2a5f] transition-all hover:bg-red-100 dark:hover:bg-[#ff2a5f]/10 uppercase tracking-[1px] font-bold">
            <div className="w-1.5 h-1.5 rounded-full bg-[#ff2a5f] animate-pulse" />
            <span className="hidden sm:inline">СИС. ЛОГ</span>
          </button>
          
          <div className="w-[1px] h-6 bg-black/10 dark:bg-white/10 mx-1"></div>
          
          <button 
            onClick={() => {
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
              window.dispatchEvent(new Event('theme-change')); // Tell map to update
            }} 
            title="Тема (Світла/Темна)" 
            className="w-10 h-10 flex items-center justify-center rounded-full border border-gray-300/50 bg-black/5 hover:bg-black/10 dark:border-white/[0.08] dark:bg-white/5 dark:hover:bg-white/10 transition-colors text-gray-800 dark:text-white/80 shrink-0"
          >
            {/* Moon Icon (Dark Mode, visible when in Light Theme) */}
            <svg viewBox="0 0 24 24" fill="currentColor" stroke="none" className="w-[18px] h-[18px] block dark:hidden opacity-80 transition-transform hover:scale-105 active:scale-95 text-[#1e293b]">
              <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>
            </svg>
            {/* Sun Icon (Light Mode, visible when in Dark Theme) */}
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="w-[18px] h-[18px] hidden dark:block opacity-80 transition-transform hover:scale-105 active:scale-95 text-white">
              <circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>
            </svg>
          </button>

          <a href={TELEGRAM_CHANNEL_URL} target="_blank" title="Telegram" className="w-10 h-10 flex items-center justify-center rounded-full bg-black/5 hover:bg-black/10 dark:bg-white/5 dark:hover:bg-white/10 transition-colors text-gray-800 dark:text-white/80">
            <svg viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4 opacity-80"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 5.42-1.13 7.19-.14.75-.42 1-.68 1.03-.58.05-1.02-.38-1.58-.75-.88-.58-1.38-.94-2.23-1.5-.99-.65-.35-1.01.22-1.59.15-.15 2.71-2.48 2.76-2.69a.2.2 0 00-.05-.18c-.06-.05-.14-.03-.21-.02-.09.02-1.49.95-4.22 2.79-.4.27-.76.41-1.08.4-.36-.01-1.04-.2-1.55-.37-.63-.2-1.12-.31-1.08-.66.02-.18.27-.36.74-.55 2.92-1.27 4.86-2.11 5.83-2.51 2.78-1.16 3.35-1.36 3.73-1.36.08 0 .27.02.39.12.1.08.13.19.14.27-.01.06.01.24 0 .38z"/></svg>
          </a>
          <a href={APP_STORE_URL} target="_blank" title="App Store" className="w-10 h-10 flex items-center justify-center rounded-full bg-black/5 hover:bg-black/10 dark:bg-white/5 dark:hover:bg-white/10 transition-colors text-gray-800 dark:text-white/80">
            <svg viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4 opacity-80"><path d="M18.71 19.5c-.83 1.24-1.71 2.45-3.05 2.47-1.34.03-1.77-.79-3.29-.79-1.53 0-2 .77-3.27.82-1.31.05-2.3-1.32-3.14-2.53C4.25 17 2.94 12.45 4.7 9.39c.87-1.52 2.43-2.48 4.12-2.51 1.28-.02 2.5.87 3.29.87.78 0 2.26-1.07 3.8-.91.65.03 2.47.26 3.64 1.98-.09.06-2.17 1.28-2.15 3.81.03 3.02 2.65 4.03 2.68 4.04-.03.07-.42 1.44-1.38 2.83M13 3.5c.73-.83 1.94-1.46 2.94-1.5.13 1.17-.34 2.35-1.04 3.19-.69.85-1.83 1.51-2.95 1.42-.15-1.15.41-2.35 1.05-3.11z"/></svg>
          </a>
          <a href={GOOGLE_PLAY_URL} target="_blank" title="Google Play" className="w-10 h-10 flex items-center justify-center rounded-full bg-black/5 hover:bg-black/10 dark:bg-white/5 dark:hover:bg-white/10 transition-colors text-gray-800 dark:text-white/80">
            <svg viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4 opacity-80"><path d="M3.609 1.814L13.792 12 3.61 22.186a.996.996 0 01-.61-.92V2.734a1 1 0 01.609-.92zm10.89 10.893l2.302 2.302-10.937 6.333 8.635-8.635zm3.199-3.199l2.302 2.302-2.302 2.302-2.698-2.698 2.698-2.698-.001.792h.001v-.792zm-3.906-3.906l10.937 6.333-2.302 2.302L13.792 5.602z"/></svg>
          </a>
          <div className="w-[1px] h-6 bg-black/10 dark:bg-white/10 mx-1"></div>
          <button onClick={onDonate} title="Підтримати" className="w-10 h-10 flex items-center justify-center rounded-full bg-[#ff2a5f]/10 dark:bg-[#ff2a5f]/10 hover:bg-[#ff2a5f]/20 dark:hover:bg-[#ff2a5f]/20 text-[#ff2a5f] transition-colors">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path></svg>
          </button>
          <button onClick={onFaq} title="Довідка" className="w-10 h-10 flex items-center justify-center rounded-full bg-black/5 hover:bg-black/10 dark:bg-white/5 dark:hover:bg-white/10 opacity-70 dark:opacity-60 transition-colors text-gray-800 dark:text-white/80">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4"><circle cx="12" cy="12" r="10"></circle><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>
          </button>
        </div>

      </div>
    </div>
  );
}
