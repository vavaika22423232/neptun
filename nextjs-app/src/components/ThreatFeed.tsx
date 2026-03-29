'use client';

import type { Marker, Alarm, BallisticThreat } from '@/types';
import { THREAT_NAMES } from '@/types';
import { getLastActivityMs } from '@/lib/marker-activity';

function formatAgo(ms: number, now: number): string {
  if (ms <= 0) return '—';
  const s = Math.floor((now - ms) / 1000);
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m`;
  return `${Math.floor(m / 60)}h`;
}

interface ThreatFeedProps {
  markers: Marker[];
  alarms: Alarm[];
  ballisticThreat: BallisticThreat | null;
}

export default function ThreatFeed({ markers, alarms, ballisticThreat }: ThreatFeedProps) {
  const now = Date.now();
  const sorted = [...markers]
    .filter(m => !['alarm', 'alarm_cancel', 'info'].includes(m.threat_type || ''))
    .sort((a, b) => getLastActivityMs(b) - getLastActivityMs(a))
    .slice(0, 15);

  const activeAlarms = alarms.filter(a => a.activeAlerts?.length).length;

  return (
    <div className="flex flex-col gap-6 w-full">

      {/* Ballistic Warning */}
      {ballisticThreat?.active && (
        <div className="flex flex-col gap-1 p-4 bg-[#ff2a5f]/10 border-l-2 border-[#ff2a5f] rounded-r-lg">
          <span className="text-[10px] font-bold tracking-widest text-[#ff2a5f] uppercase">
            Балістична загроза
          </span>
          <span className="text-sm font-medium text-gray-900 dark:text-white">
            {ballisticThreat.region || 'Нецільова траєкторія'}
          </span>
        </div>
      )}

      {/* Feed List */}
      <div className="flex flex-col gap-4">
        <div className="text-[10px] font-bold tracking-widest text-gray-500 dark:text-white/40 uppercase">
          Активні об'єкти
        </div>

        {sorted.length === 0 ? (
          <div className="text-sm text-gray-400 dark:text-white/30">Радар чистий.</div>
        ) : (
          <div className="flex flex-col">
            {sorted.map(m => {
              const t = m.threat_type || 'default';
              const ts = getLastActivityMs(m);
              return (
                <div key={`${m.id || m.track_id}_${ts}`} className="group flex items-center justify-between py-3 border-b border-gray-100 dark:border-white/[0.04] last:border-0 hover:bg-black/[0.02] dark:hover:bg-white/[0.02] transition-colors -mx-2 px-2 rounded-lg cursor-default">
                  <div className="flex flex-col gap-0.5">
                    <span className="text-sm font-medium text-gray-800 dark:text-white/90 group-hover:text-black dark:group-hover:text-white transition-colors">
                      {THREAT_NAMES[t] || t}
                    </span>
                    <span className="text-[11px] text-gray-500 dark:text-white/40">
                      {[m.place, m.region].filter(Boolean).join(' · ') || 'Невідомо'}
                    </span>
                  </div>
                  <div className="text-[11px] font-mono text-gray-400 dark:text-white/30 tabular-nums">
                    {formatAgo(ts, now)}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
