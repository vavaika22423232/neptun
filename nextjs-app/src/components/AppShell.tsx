'use client';

import React, { useState, useMemo } from 'react';
import type { Marker, Alarm, BallisticThreat, PresenceData } from '@/types';
import ThreatFeed from './ThreatFeed';
import TelegramBanner from './TelegramBanner';
import BottomBar from './BottomBar';
import MapAtmosphereOverlay from './MapAtmosphereOverlay';

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
  const activeAlarms = useMemo(() => alarms.filter(a => a.activeAlerts?.length > 0).length, [alarms]);
  const hasThreats = markers.length > 0 || activeAlarms > 0;

  return (
    <div className="relative h-[100dvh] w-full overflow-hidden text-gray-900 dark:text-white font-sans selection:bg-[#ff2a5f]/30 transition-colors duration-300">
      
      {/* 100% Immersive Map Background */}
      <main className="absolute inset-0 z-0">
        {children}
        <MapAtmosphereOverlay />
      </main>

      {/* Floating HUD Layer */}
      <div className="pointer-events-none absolute inset-0 z-[2000] flex flex-col items-center justify-between p-6 pb-20 md:p-8">
        
        {/* Top Control Center — компактна капсула */}
        <div className="relative w-full max-w-[360px] shrink-0">
          
          {/* Main Capsule */}
          <div 
            className={`pointer-events-auto flex flex-col overflow-hidden transition-all duration-500 will-change-transform ease-[cubic-bezier(0.16,1,0.3,1)]
              bg-white/45 border border-gray-200/30 shadow-[0_8px_32px_rgba(0,0,0,0.06),inset_0_1px_0_rgba(255,255,255,0.35)]
              dark:bg-[#0a0a0b]/50 dark:border-white/[0.06] dark:shadow-[0_16px_48px_rgba(0,0,0,0.35),inset_0_1px_0_rgba(255,255,255,0.04)]
              backdrop-blur-lg
              ${expanded ? 'rounded-[28px] h-[min(580px,85dvh)] md:h-[min(640px,85dvh)]' : 'rounded-[24px] h-[116px]'}
            `}
          >
            {/* Capsule Header (Always Visible) */}
            <div className="flex flex-col shrink-0">
              <div 
                className="h-12 px-4 flex items-center justify-between cursor-pointer"
                onClick={() => setExpanded(!expanded)}
              >
                <span className="text-[13px] font-bold tracking-[0.18em] uppercase text-gray-900 dark:text-white">NEPTUN</span>
                
                <div className="flex items-center gap-2 sm:gap-3">
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
              className={`overflow-y-auto scrollbar-none transition-opacity duration-300
                ${expanded ? 'min-h-0 flex-1 px-4 pb-4 pt-1 opacity-100 delay-200' : 'h-0 shrink-0 overflow-hidden p-0 opacity-0 pointer-events-none'}
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

        <BottomBar onDonate={onDonate} onFaq={onFaq} />

      </div>
    </div>
  );
}
