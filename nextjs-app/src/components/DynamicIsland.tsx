'use client';

import { useState, useMemo } from 'react';
import type { Alarm, Marker, PresenceData } from '@/types';
import { THREAT_NAMES } from '@/types';
import { getLastActivityMs } from '@/lib/marker-activity';
import { glass } from '@/lib/glassSurface';

function countActiveAlarms(alarms: Alarm[]): number {
  let n = 0;
  for (const a of alarms) {
    if (a.activeAlerts?.length) n += 1;
  }
  return n;
}

export default function DynamicIsland({
  alarms,
  markers,
  presence,
}: {
  alarms: Alarm[];
  markers: Marker[];
  presence: PresenceData;
}) {
  const [expanded, setExpanded] = useState(false);

  const activeRegions = countActiveAlarms(alarms);
  const now = Date.now();

  const feed = useMemo(() => {
    const list = [...markers].filter((m) => {
      const t = m.threat_type || '';
      return !['alarm', 'alarm_cancel', 'info'].includes(t);
    });
    list.sort((a, b) => getLastActivityMs(b) - getLastActivityMs(a));
    return list.slice(0, 8);
  }, [markers]);

  return (
    <>
      {/* Backdrop for explicit focus when expanded */}
      <div
        className={`fixed inset-0 z-[1490] bg-[#000000]/40 backdrop-blur-md transition-opacity duration-500 ${
          expanded ? 'pointer-events-auto opacity-100' : 'pointer-events-none opacity-0'
        }`}
        onClick={() => setExpanded(false)}
      />

      <div
        className={`fixed top-safe pt-4 left-1/2 z-[1500] -translate-x-1/2 flex justify-center transition-all duration-[600ms] ease-[cubic-bezier(0.16,1,0.3,1)] ${
          expanded ? 'w-[400px] max-w-[95vw]' : 'w-auto'
        }`}
      >
        <div
          onClick={() => !expanded && setExpanded(true)}
          className={`relative overflow-hidden cursor-pointer transition-all duration-[600ms] ease-[cubic-bezier(0.16,1,0.3,1)] ${
            expanded ? glass.panel + ' h-[520px] w-full p-6 flex flex-col cursor-default' : glass.island + ' h-[56px] px-6 flex items-center gap-6'
          }`}
        >
          {/* Unexpanded (Pill) State */}
          <div
            className={`flex items-center gap-6 whitespace-nowrap transition-all duration-[400ms] absolute top-1/2 -translate-y-1/2 left-6 ${
              expanded ? 'opacity-0 scale-95 pointer-events-none' : 'opacity-100 scale-100 delay-150'
            }`}
          >
            <div className="flex items-center gap-2">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[#ff2a5f]/60"></span>
                <span className="relative inline-flex h-2 w-2 rounded-full bg-[#ff2a5f] shadow-[0_0_8px_rgba(255,42,95,0.8)]"></span>
              </span>
              <span className="text-[14px] font-semibold text-white tracking-wide">
                Тривоги: <span className="text-[#ff2a5f] ml-1">{activeRegions}</span>
              </span>
            </div>

            <div className="flex items-center gap-2 border-l border-white/10 pl-6">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[#69f0ae]/50"></span>
                <span className="relative inline-flex h-2 w-2 rounded-full bg-[#69f0ae] shadow-[0_0_8px_rgba(105,240,174,0.6)]"></span>
              </span>
              <span className="text-[14px] font-medium text-white/80 tracking-wide">
                Онлайн: {presence.total}
              </span>
            </div>
            
            <div className="text-white/30 hover:text-white/80 transition-colors ml-2">
               <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4"><polyline points="6 9 12 15 18 9"></polyline></svg>
            </div>
          </div>

          {/* Expanded (Panel) State */}
          <div
            className={`flex flex-col h-full w-full transition-all duration-[500ms] delay-100 ${
              expanded ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8 pointer-events-none absolute'
            }`}
          >
            <div className="flex justify-between items-center mb-8">
              <h2 className="text-xl font-bold text-white tracking-[0.1em]">СИТУАЦІЯ</h2>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setExpanded(false);
                }}
                className={`w-8 h-8 flex items-center justify-center ${glass.button}`}
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
              </button>
            </div>

            <div className="grid grid-cols-2 gap-4 mb-8">
              <div className={`${glass.card} p-4 flex flex-col items-center justify-center`}>
                <span className="text-[11px] font-bold text-white/40 uppercase tracking-widest mb-1">Регіони</span>
                <span className="text-4xl font-bold text-[#ff2a5f] tabular-nums">{activeRegions}</span>
              </div>
              <div className={`${glass.card} p-4 flex flex-col items-center justify-center`}>
                <span className="text-[11px] font-bold text-white/40 uppercase tracking-widest mb-1">Цілі</span>
                <span className="text-4xl font-bold text-white tabular-nums">{markers.length}</span>
              </div>
            </div>

            <h3 className="text-[11px] font-bold text-white/40 uppercase tracking-widest mb-3 px-1">Останні події</h3>
            <div className="flex-1 overflow-y-auto scrollbar-none pr-2 space-y-3">
              {feed.length === 0 ? (
                <div className="text-center text-white/40 py-8 text-sm">Небо чисте</div>
              ) : (
                feed.map(m => {
                  const t = m.threat_type || 'default';
                  const ts = getLastActivityMs(m);
                  return (
                    <div key={`${m.id || m.track_id}_${m.lat}_${m.lng}_${ts}`} className={`${glass.tile} p-3 flex justify-between items-center`}>
                      <div className="flex flex-col gap-1">
                        <span className="text-sm font-semibold text-white/90">{THREAT_NAMES[t] || t}</span>
                        <span className="text-[11px] text-white/50">{[m.place, m.region].filter(Boolean).join(' · ') || 'Невідома локація'}</span>
                      </div>
                      <div className="text-[10px] text-white/30 uppercase font-medium">
                         {ts > 0 ? new Date(ts).toLocaleTimeString('uk-UA', { hour: '2-digit', minute: '2-digit' }) : ''}
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
