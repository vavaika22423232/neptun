'use client';

import { useMemo } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import type { Alarm, BallisticThreat, Marker, PresenceData } from '@/types';
import { THREAT_NAMES } from '@/types';
import { TELEGRAM_CHANNEL_URL } from '@/lib/constants';
import { trackedAppStoreUrl, trackedGooglePlayUrl } from '@/lib/app-download-urls';
import { getLastActivityMs } from '@/lib/marker-activity';
import { glass } from '@/lib/glassSurface';

function formatAgo(ms: number, now: number): string {
  if (ms <= 0) return '—';
  const s = Math.floor((now - ms) / 1000);
  if (s < 60) return `${s} с тому`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m} хв тому`;
  const h = Math.floor(m / 60);
  if (h < 48) return `${h} год тому`;
  return `${Math.floor(h / 24)} д тому`;
}

function countActiveAlarms(alarms: Alarm[]): number {
  let n = 0;
  for (const a of alarms) {
    if (a.activeAlerts?.length) n += 1;
  }
  return n;
}

function aggregateByType(markers: Marker[]): Record<string, number> {
  const out: Record<string, number> = {};
  for (const m of markers) {
    const t = m.threat_type || 'default';
    out[t] = (out[t] || 0) + 1;
  }
  return out;
}

interface DashboardSidebarProps {
  markers: Marker[];
  alarms: Alarm[];
  ballisticThreat: BallisticThreat | null;
  presence: PresenceData;
  onDonate: () => void;
  onFaq: () => void;
}

export default function DashboardSidebar({
  markers,
  alarms,
  ballisticThreat,
  presence,
  onDonate,
  onFaq,
}: DashboardSidebarProps) {
  const pathname = usePathname();
  const isUk = pathname !== '/en' && !pathname?.startsWith('/en/');
  const now = Date.now();

  const alarmRegions = countActiveAlarms(alarms);
  const byType = useMemo(() => aggregateByType(markers), [markers]);
  const topTypes = useMemo(() => {
    return Object.entries(byType)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 6);
  }, [byType]);

  const feed = useMemo(() => {
    const list = [...markers].filter((m) => {
      const t = m.threat_type || '';
      return !['alarm', 'alarm_cancel', 'info'].includes(t);
    });
    list.sort((a, b) => getLastActivityMs(b) - getLastActivityMs(a));
    return list.slice(0, 14);
  }, [markers]);

  return (
    <aside className="fixed inset-x-0 bottom-0 z-[1000] flex max-h-[60vh] flex-col overflow-hidden sm:relative sm:max-h-none sm:w-[400px] sm:shrink-0 sm:border-r sm:border-white/[0.06] sm:bg-black/30 sm:backdrop-blur-3xl lg:w-[450px]">
      
      {/* Mobile Dragger */}
      <div className="w-full flex justify-center py-2 sm:hidden bg-black/50 backdrop-blur-xl border-t border-white/10 rounded-t-[24px]">
        <div className="h-1.5 w-12 rounded-full bg-white/20"></div>
      </div>

      <div className="flex-1 overflow-y-auto px-4 pb-6 pt-2 scrollbar-none sm:px-6 sm:py-6 bg-black/50 sm:bg-transparent backdrop-blur-xl sm:backdrop-blur-none">
        
        {/* Header Options */}
        <header className="mb-6 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-xl font-bold tracking-[0.2em] text-white">NEPTUN</span>
            <div className="flex items-center gap-1.5 text-[10px] text-white/50">
              <span className="relative flex h-1.5 w-1.5">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[#69f0ae]/35"></span>
                <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-[#69f0ae] shadow-[0_0_6px_rgba(105,240,174,0.45)]"></span>
              </span>
              <span className="font-medium text-white/80">{presence.total}</span>
              <span>онлайн</span>
            </div>
          </div>
          <div className="flex gap-2">
            <button onClick={onFaq} className="flex h-8 w-8 items-center justify-center rounded-[12px] bg-white/[0.05] border border-white/[0.05] text-white/60 hover:text-white hover:bg-white/10 transition">
              <span className="material-icons text-[18px]">help_outline</span>
            </button>
            <button onClick={onDonate} className="flex h-8 w-8 items-center justify-center rounded-[12px] bg-[#ff2a5f]/10 border border-[#ff2a5f]/20 text-[#ff2a5f] hover:bg-[#ff2a5f]/20 transition">
              <span className="material-icons text-[18px]">favorite</span>
            </button>
          </div>
        </header>

        {/* Bento Grid Metrics */}
        <div className="mb-6 grid grid-cols-2 gap-3">
          <div className={`${glass.tile} p-3`}>
            <div className="text-[10px] uppercase tracking-wider text-white/40">Тривоги</div>
            <div className="mt-1 text-2xl font-semibold text-white tabular-nums">{alarmRegions}</div>
            <div className="mt-0.5 text-[11px] text-white/50">активні регіони</div>
          </div>
          <div className={`${glass.tile} p-3`}>
            <div className="text-[10px] uppercase tracking-wider text-white/40">Об'єкти</div>
            <div className="mt-1 text-2xl font-semibold text-white tabular-nums">{markers.length}</div>
            <div className="mt-0.5 text-[11px] text-white/50">треки та події</div>
          </div>
          <div className={`col-span-2 ${glass.tile} flex items-center justify-between p-3 ${ballisticThreat?.active ? '!bg-[#ff3b30]/15 !border-[#ff3b30]/30' : ''}`}>
            <div>
              <div className="text-[10px] uppercase tracking-wider text-white/40">Балістика</div>
              <div className="mt-0.5 text-[12px] text-white/70">
                {ballisticThreat?.active ? ballisticThreat.region || 'Загроза балістики' : 'Поки чисто'}
              </div>
            </div>
            <div className={`text-sm font-semibold ${ballisticThreat?.active ? 'text-[#ff3b30]' : 'text-[#69f0ae]'}`}>
              {ballisticThreat?.active ? 'ТАК' : 'НІ'}
            </div>
          </div>
        </div>

        {/* Threat Types Breakdown */}
        {topTypes.length > 0 && (
          <div className="mb-6">
            <h3 className="mb-3 text-[10px] font-bold uppercase tracking-wider text-white/30">Активні цілі (Підсумок)</h3>
            <ul className="space-y-2">
              {topTypes.map(([t, c]) => (
                <li key={t} className={`flex items-center justify-between px-3 py-2 ${glass.tile}`}>
                  <span className="text-[13px] text-white/80">{THREAT_NAMES[t] || t}</span>
                  <span className="font-bold text-[#ff2a5f]">{c}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Feed */}
        <div className="mb-6">
          <h3 className="mb-3 text-[10px] font-bold uppercase tracking-wider text-white/30">Стрічка оновлень</h3>
          <ul className="space-y-2">
            {feed.length === 0 ? (
              <li className="py-4 text-center text-[12px] text-white/40">Повітряний простір чистий</li>
            ) : (
              feed.map((m) => {
                const t = m.threat_type || 'default';
                const ts = getLastActivityMs(m);
                const stale = ts > 0 && now - ts > 10 * 60 * 1000;
                return (
                  <li key={`${m.track_id || m.id || ''}_${m.lat}_${m.lng}_${t}`} className={`flex flex-col gap-1 px-3 py-2.5 ${glass.tile}`}>
                    <div className="flex items-center justify-between text-[12px]">
                      <span className="font-medium text-white">{THREAT_NAMES[t] || t}</span>
                      <span className="tabular-nums text-white/40">{formatAgo(ts, now)}</span>
                    </div>
                    <div className="text-[11px] text-white/60">
                      {[m.place, m.region].filter(Boolean).join(' · ') || `${Number(m.lat).toFixed(2)}°, ${Number(m.lng).toFixed(2)}°`}
                      {stale && <span className="ml-1 text-[#ff3b30]/80">· стале</span>}
                    </div>
                  </li>
                );
              })
            )}
          </ul>
        </div>

        {/* App Links */}
        <div className="mt-8 mb-4 grid grid-cols-2 gap-3">
          <a href={trackedAppStoreUrl('dashboard_sidebar')} target="_blank" rel="noopener noreferrer" data-neptun-app-cta="dashboard_sidebar" data-neptun-store="app_store" className={`flex flex-col items-center justify-center p-3 text-center transition ${glass.tile}`}>
            <span className="mb-1 bg-gradient-to-br from-brand-300 to-brand-500 bg-clip-text text-xl font-bold tracking-widest text-transparent">N</span>
            <span className="text-[11px] text-white/60">App Store</span>
          </a>
          <a href={trackedGooglePlayUrl('dashboard_sidebar')} target="_blank" rel="noopener noreferrer" data-neptun-app-cta="dashboard_sidebar" data-neptun-store="google_play" className={`flex flex-col items-center justify-center p-3 text-center transition ${glass.tile}`}>
            <span className="mb-1 text-xl font-bold tracking-widest text-[#69f0ae]">N</span>
            <span className="text-[11px] text-white/60">Google Play</span>
          </a>
        </div>
      </div>
    </aside>
  );
}
