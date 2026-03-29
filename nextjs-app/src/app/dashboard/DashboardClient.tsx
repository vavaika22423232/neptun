'use client';

import { useMemo, useEffect, memo } from 'react';
import { useAlarms } from '@/hooks/useAlarms';
import { useMarkers } from '@/hooks/useMarkers';
import type { Marker } from '@/types';
import { THREAT_NAMES } from '@/types';

// ── Threat type grouping ─────────────────────────────────────
function countThreats(markers: Marker[]) {
  const counts: Record<string, number> = {};
  for (const m of markers) {
    const t = m.threat_type || 'default';
    counts[t] = (counts[t] || 0) + (m.count || 1);
  }
  return counts;
}

function threatColor(type: string, active: boolean): string {
  if (!active) return 'var(--outline)';
  const map: Record<string, string> = {
    ballistic: '#ff5252',
    raketa: '#ff5252',
    pusk: '#ff5252',
    missile: '#ff5252',
    avia: '#ffca28',
    shahed: 'var(--primary)',
    drone: 'var(--primary)',
    uav: 'var(--primary)',
    kab: '#ff6b35',
    rszv: '#ff6b35',
  };
  return map[type] || 'var(--primary)';
}

// ── Format time ──────────────────────────────────────────────
function fmtTime(marker: Marker): string {
  if (marker.date) {
    const d = new Date(marker.date);
    if (!isNaN(d.getTime())) {
      return `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`;
    }
    const match = marker.date.match(/(\d{1,2}):(\d{2})/);
    if (match) return `${match[1].padStart(2, '0')}:${match[2]}`;
  }
  return '';
}

// ══════════════════════════════════════════════════════════════
export default function DashboardClient({
  isEmbed = false,
  theme = 'dark',
}: {
  isEmbed?: boolean;
  theme?: 'light' | 'dark';
}) {
  const { alarms } = useAlarms();

  // Apply theme when embed=1 — force CSS variables directly as inline styles
  useEffect(() => {
    if (!isEmbed) return;
    const root = document.documentElement;
    root.classList.add('theme-light');
    root.classList.remove('dark');
    if (theme === 'light') {
      // Force all CSS variables inline — overrides any class/specificity issues
      const lightVars: Record<string, string> = {
        '--surface': '#f5f7fa',
        '--surface-dim': '#e8ecf0',
        '--surface-container-lowest': '#ffffff',
        '--surface-container-low': '#f0f3f8',
        '--surface-container': '#e8ecf2',
        '--surface-container-high': '#e0e5ec',
        '--surface-container-highest': '#d8dee6',
        '--on-surface': '#1a1d24',
        '--on-surface-variant': '#4a4e58',
        '--outline': '#6c7079',
        '--outline-variant': '#a8acb4',
        '--primary': '#00668a',
        '--primary-container': '#b8e5ff',
        '--on-primary': '#ffffff',
        '--on-primary-container': '#003548',
        '--secondary': '#8b5a00',
        '--secondary-container': '#ffddb3',
        '--on-secondary-container': '#2b1700',
        '--tertiary': '#9e0042',
        '--tertiary-container': '#ffd9e6',
        '--on-tertiary-container': '#3d0019',
        '--error': '#ba1a1a',
        '--error-container': '#ffdad6',
        '--on-error-container': '#410002',
      };
      for (const [k, v] of Object.entries(lightVars)) {
        root.style.setProperty(k, v);
      }
    } else {
      // Remove inline overrides so :root dark defaults apply
      const vars = ['--surface', '--surface-dim', '--surface-container-lowest',
        '--surface-container-low', '--surface-container', '--surface-container-high',
        '--surface-container-highest', '--on-surface', '--on-surface-variant',
        '--outline', '--outline-variant', '--primary', '--primary-container',
        '--on-primary', '--on-primary-container', '--secondary', '--secondary-container',
        '--on-secondary-container', '--tertiary', '--tertiary-container',
        '--on-tertiary-container', '--error', '--error-container', '--on-error-container'];
      for (const v of vars) {
        root.style.removeProperty(v);
      }
      root.classList.remove('theme-light');
      root.classList.add('dark');
    }
    document.body.style.background = 'var(--surface-dim)';
    document.body.style.color = 'var(--on-surface)';
  }, [isEmbed, theme]);
  const { markers, ballisticThreat } = useMarkers();

  const counts = useMemo(() => countThreats(markers), [markers]);

  const shahedCount = (counts.shahed || 0) + (counts.drone || 0) + (counts.uav || 0) + (counts.fpv || 0);
  const raketaCount = (counts.raketa || 0) + (counts.missile || 0) + (counts.pusk || 0) + (counts.launch || 0);
  const kabCount = (counts.kab || 0) + (counts.rszv || 0);
  const aviaCount = counts.avia || 0;
  const totalCount = markers.length;

  const ballisticActive = !!ballisticThreat?.active;

  // Alarm state count
  const alarmStateCount = useMemo(() => {
    const states = new Set<string>();
    alarms.forEach((a) => {
      if (a.regionType === 'State' && a.activeAlerts?.length > 0) {
        states.add(a.regionId);
      }
    });
    return states.size;
  }, [alarms]);

  // Recent threats (sorted by date desc)
  const recentThreats = useMemo(() => {
    const sorted = [...markers].sort((a, b) => {
      const da = a.date ? new Date(a.date).getTime() : 0;
      const db = b.date ? new Date(b.date).getTime() : 0;
      return db - da;
    });
    return sorted.slice(0, 10);
  }, [markers]);

  const hasThreats = totalCount > 0 || ballisticActive;
  const hasAlarm = alarmStateCount > 0;

  const heroColor = (hasAlarm || ballisticActive) ? '#ff5252' : hasThreats ? '#ffca28' : '#4caf50';
  const heroLabel = hasAlarm ? 'ПОВІТРЯНА ТРИВОГА' : hasThreats ? 'ЗАГРОЗИ В ПОВІТРІ' : 'ВІДБІЙ';

  return (
    <div className={`dash-page ${isEmbed ? 'dash-embed' : ''}`}>
      {!isEmbed && (
        <div className="dash-header">
          <h1>Дашборд</h1>
        </div>
      )}

      <div className="dash-scroll">
        {/* Hero – alarm status */}
        <div className="dash-hero" style={{ borderColor: `${heroColor}33`, background: `${heroColor}0f` }}>
          <div className="dash-hero-top">
            <span className="dash-hero-dot" style={{ background: heroColor }} />
            <span className="dash-hero-label" style={{ color: heroColor }}>{heroLabel}</span>
          </div>
          <div className="dash-hero-count">
            <span className="dash-hero-num" style={{ color: heroColor }}>{totalCount}</span>
            <span className="dash-hero-sub">{hasThreats ? 'загроз в повітрі' : 'чисте небо'}</span>
          </div>
          {hasAlarm && (
            <div className="dash-hero-extra" style={{ color: `${heroColor}bb` }}>
              {alarmStateCount} обл. під тривогою
            </div>
          )}
          {ballisticThreat?.region && (
            <div className="dash-hero-extra" style={{ color: '#ff5252', fontWeight: 600 }}>
              ⚡ Балістика: {ballisticThreat.region}
            </div>
          )}
        </div>

        {/* Threat Grid 2×2 */}
        <div className="dash-grid">
          <ThreatCard label="БАЛІСТИКА" count={raketaCount} active={ballisticActive || raketaCount > 0} icon="🚀" color={threatColor('raketa', ballisticActive || raketaCount > 0)} critical={ballisticActive} />
          <ThreatCard label="АВІАЦІЯ" count={aviaCount} active={aviaCount > 0} icon="✈️" color={threatColor('avia', aviaCount > 0)} />
          <ThreatCard label="ШАХЕДИ / БПЛА" count={shahedCount} active={shahedCount > 0} icon="🛩️" color={threatColor('shahed', shahedCount > 0)} />
          <ThreatCard label="КАБ / РСЗВ" count={kabCount} active={kabCount > 0} icon="💣" color={threatColor('kab', kabCount > 0)} />
        </div>

        {/* Event Feed */}
        <div className="dash-feed">
          <div className="dash-feed-header">
            <span>📡</span> СТРІЧКА ПОДІЙ
          </div>
          {recentThreats.length === 0 ? (
            <div className="dash-feed-empty">
              <span>✅</span>
              <p>Немає активних загроз</p>
            </div>
          ) : (
            recentThreats.map((m, i) => (
              <EventRow key={m.id || i} marker={m} />
            ))
          )}
        </div>

        {/* Quick actions */}
        {!isEmbed && (
          <div className="dash-actions">
            <a href="https://t.me/+Q0PcuV4OkuxmYjVi" target="_blank" rel="noopener" className="dash-action-btn">
              <span>📨</span> Telegram
            </a>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Threat card ──────────────────────────────────────────────
const ThreatCard = memo(function ThreatCard({
  label,
  count,
  active,
  icon,
  color,
  critical,
}: {
  label: string;
  count: number;
  active: boolean;
  icon: string;
  color: string;
  critical?: boolean;
}) {
  return (
    <div
      className={`dash-threat-card ${active ? 'active' : ''} ${critical ? 'critical' : ''}`}
      style={{
        borderColor: active ? `${color}44` : undefined,
        background: active ? `${color}14` : undefined,
      }}
    >
      <div className="dash-threat-top">
        <span className="dash-threat-icon">{icon}</span>
        {count > 0 && <span className="dash-threat-count" style={{ color }}>{count}</span>}
      </div>
      <div className="dash-threat-label" style={{ color: active ? color : undefined }}>
        {label}
      </div>
    </div>
  );
});

// ── Event row ────────────────────────────────────────────────
const EventRow = memo(function EventRow({ marker }: { marker: Marker }) {
  const typeName = THREAT_NAMES[marker.threat_type] || marker.threat_type;
  const place = marker.place || marker.region || 'Невідомо';
  const time = fmtTime(marker);

  return (
    <div className="dash-event">
      <div className="dash-event-text">
        <span className="dash-event-place">{place} — {typeName}</span>
        {marker.text && <span className="dash-event-detail">{marker.text}</span>}
      </div>
      <span className="dash-event-time">{time}</span>
    </div>
  );
});
