'use client';

import React, { useMemo } from 'react';
import type { Marker, Alarm, BallisticThreat, PresenceData } from '@/types';
import BottomBar from './BottomBar';

interface AppShellProps {
  markers: Marker[];
  alarms: Alarm[];
  presence: PresenceData;
  ballisticThreat: BallisticThreat | null;
  onDonate: () => void;
  onFaq: () => void;
  onToggleUkraineOnly: () => void;
  ukraineOnly: boolean;
  children: React.ReactNode;
}

export default function AppShell({
  markers,
  alarms,
  presence,
  ballisticThreat,
  onDonate,
  onFaq,
  onToggleUkraineOnly,
  ukraineOnly,
  children,
}: AppShellProps) {
  const activeAlarms = useMemo(() => alarms.filter(a => a.activeAlerts?.length > 0).length, [alarms]);
  void ballisticThreat;

  return (
    <div className="relative h-[100dvh] w-full overflow-hidden font-sans text-[var(--on-surface)] selection:bg-[#ff2a5f]/30 transition-colors duration-300">
      
      {/* 100% Immersive Map Background */}
      <main className="absolute inset-0 z-0">
        {children}
      </main>

      {/* Floating HUD Layer */}
      <div className="pointer-events-none absolute inset-0 z-[2000]">
        <div className="absolute left-1/2 top-[calc(env(safe-area-inset-top,0px)+0.75rem)] flex -translate-x-1/2 items-center gap-2 text-[12px] font-black uppercase tracking-[0.28em] text-[var(--hud-brand-text)] [text-shadow:var(--hud-brand-shadow)] sm:hidden">
          <span className="block h-3.5 w-5 overflow-hidden rounded-[3px] shadow-[0_1px_8px_rgba(0,0,0,0.42)]" aria-label="Прапор України" role="img">
            <span className="block h-1/2 bg-[#198de5]" />
            <span className="block h-1/2 bg-[#ffd43b]" />
          </span>
          <span>NEPTUN.IN.UA</span>
        </div>

        <BottomBar
          onDonate={onDonate}
          onFaq={onFaq}
          onToggleUkraineOnly={onToggleUkraineOnly}
          activeAlarms={activeAlarms}
          targetsCount={markers.length}
          onlineCount={presence.total ?? 0}
          ukraineOnly={ukraineOnly}
        />
      </div>
    </div>
  );
}
