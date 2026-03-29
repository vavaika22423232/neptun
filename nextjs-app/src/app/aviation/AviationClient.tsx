'use client';

import { useState, useEffect, useCallback, useMemo } from 'react';
import { useSearchParams } from 'next/navigation';
import { THREAT_NAMES } from '@/types';

interface ThreatData {
  summary: {
    drones: number;
    missiles: number;
    kab: number;
    ballistic: number;
    avia: number;
  };
  threats: ThreatItem[];
  total: number;
  updated_at: string;
}

interface ThreatItem {
  id?: string;
  type: string;
  place: string;
  region: string;
  text: string;
  date: string;
  description: string;
  course_direction?: string;
  speed_kmh?: number;
}

const EMPTY: ThreatData = {
  summary: { drones: 0, missiles: 0, kab: 0, ballistic: 0, avia: 0 },
  threats: [],
  total: 0,
  updated_at: '',
};

function fmtTime(dateStr: string): string {
  const d = new Date(dateStr);
  if (isNaN(d.getTime())) {
    const m = dateStr.match(/(\d{1,2}):(\d{2})/);
    return m ? `${m[1].padStart(2, '0')}:${m[2]}` : '';
  }
  return `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`;
}

const THREAT_EMOJI: Record<string, string> = {
  shahed: '🛩️', drone: '🛩️', uav: '🛩️', fpv: '🎯',
  raketa: '🚀', missile: '🚀', pusk: '🚀', launch: '🚀',
  ballistic: '☄️', avia: '✈️',
  kab: '💣', rszv: '💣',
  rozved: '🔍', vibuh: '💥', explosion: '💥',
  obstril: '💥', artillery: '💥',
};

export default function AviationClient() {
  const searchParams = useSearchParams();
  const isEmbed = searchParams.get('embed') === '1';
  const [data, setData] = useState<ThreatData>(EMPTY);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const fetchThreats = useCallback(async () => {
    // Skip fetch when tab is hidden — saves server requests during background tabs
    if (typeof document !== 'undefined' && document.visibilityState === 'hidden') return;
    try {
      const res = await fetch('/api/threats');
      if (!res.ok) throw new Error('HTTP error');
      const json = await res.json();
      setData({
        summary: json.summary || EMPTY.summary,
        threats: json.threats || [],
        total: json.total || 0,
        updated_at: json.updated_at || '',
      });
      setError(false);
    } catch {
      setError(true);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchThreats();
    const iv = setInterval(fetchThreats, 30_000);
    return () => clearInterval(iv);
  }, [fetchThreats]);

  const { summary, threats, total } = data;
  const hasAnyThreat = total > 0;

  // Detect strategic aviation / MiG-31K from descriptions
  const strategicAviation = useMemo(() => {
    return threats.some(
      (t) =>
        /ту-95|tu-95|ту-160|tu-160|стратегічн/i.test(t.description)
    );
  }, [threats]);

  const mig31k = useMemo(() => {
    return threats.some(
      (t) => /міг-31|mig-31|кинджал|kinzhal/i.test(t.description)
    );
  }, [threats]);

  // Group threats by category
  const criticalThreats = threats.filter(
    (t) => ['ballistic', 'pusk', 'launch'].includes(t.type)
  );
  const airThreats = threats.filter(
    (t) => ['avia', 'kab', 'rszv'].includes(t.type)
  );
  const droneThreats = threats.filter(
    (t) => ['shahed', 'drone', 'uav', 'fpv', 'rozved'].includes(t.type)
  );
  const otherThreats = threats.filter(
    (t) =>
      !['ballistic', 'pusk', 'launch', 'avia', 'kab', 'rszv', 'shahed', 'drone', 'uav', 'fpv', 'rozved'].includes(t.type)
  );

  return (
    <div className={`avia-page ${isEmbed ? 'avia-embed' : ''}`}>
      {!isEmbed && (
        <div className="avia-header">
          <h1>✈️ Авіаційна обстановка</h1>
        </div>
      )}

      <div className="avia-scroll">
        {loading && (
          <div className="avia-loading">
            <div className="chat-spinner" />
            <span>Завантаження...</span>
          </div>
        )}

        {!loading && error && (
          <div className="avia-empty">
            <div className="avia-empty-icon">⚠️</div>
            <p>Помилка завантаження даних</p>
            <button onClick={fetchThreats} style={{ color: 'var(--primary)', background: 'none', border: 'none', cursor: 'pointer', fontSize: 14 }}>
              Спробувати знову
            </button>
          </div>
        )}

        {!loading && !error && !hasAnyThreat && (
          <div className="avia-empty">
            <div className="avia-empty-icon">✅</div>
            <p>Чисте небо</p>
            <p style={{ fontSize: 13, opacity: 0.6 }}>Загроз не виявлено</p>
          </div>
        )}

        {!loading && !error && hasAnyThreat && (
          <>
            {/* Summary cards */}
            <div className="dash-grid" style={{ marginBottom: 20 }}>
              <SummaryCard label="БАЛІСТИКА" count={summary.ballistic} icon="☄️" active={summary.ballistic > 0} color="#ff5252" critical />
              <SummaryCard label="АВІАЦІЯ" count={summary.avia} icon="✈️" active={summary.avia > 0 || strategicAviation} color="#ffca28" />
              <SummaryCard label="ДРОНИ / БПЛА" count={summary.drones} icon="🛩️" active={summary.drones > 0} color="var(--primary)" />
              <SummaryCard label="КАБ / РСЗВ" count={summary.kab} icon="💣" active={summary.kab > 0} color="#ff6b35" />
            </div>

            {/* Strategic aviation alert */}
            {strategicAviation && (
              <div className="avia-card" style={{ borderColor: '#ff525244', background: '#ff52520f' }}>
                <div className="avia-card-icon" style={{ background: '#ff525222' }}>⚡</div>
                <div className="avia-card-body">
                  <div className="avia-card-title" style={{ color: '#ff5252', fontWeight: 600 }}>Стратегічна авіація</div>
                  <div className="avia-card-sub">Ту-95МС / Ту-160 — зафіксовано активність</div>
                </div>
              </div>
            )}

            {mig31k && (
              <div className="avia-card" style={{ borderColor: '#ff525244', background: '#ff52520f' }}>
                <div className="avia-card-icon" style={{ background: '#ff525222' }}>🎯</div>
                <div className="avia-card-body">
                  <div className="avia-card-title" style={{ color: '#ff5252', fontWeight: 600 }}>МіГ-31К</div>
                  <div className="avia-card-sub">Носій «Кинджал» — зафіксовано активність</div>
                </div>
              </div>
            )}

            {/* Critical threats */}
            {criticalThreats.length > 0 && (
              <ThreatSection title="КРИТИЧНІ ЗАГРОЗИ" color="#ff5252" threats={criticalThreats} />
            )}

            {/* Air threats */}
            {airThreats.length > 0 && (
              <ThreatSection title="АВІАЦІЙНІ ЗАГРОЗИ" color="#ffca28" threats={airThreats} />
            )}

            {/* Drones */}
            {droneThreats.length > 0 && (
              <ThreatSection title="БПЛА / ДРОНИ" color="var(--primary)" threats={droneThreats} />
            )}

            {/* Other */}
            {otherThreats.length > 0 && (
              <ThreatSection title="ІНШІ ЗАГРОЗИ" color="var(--on-surface-variant)" threats={otherThreats} />
            )}
          </>
        )}
      </div>
    </div>
  );
}

// ── Summary card ─────────────────────────────────────────────
function SummaryCard({
  label, count, icon, active, color, critical,
}: {
  label: string; count: number; icon: string; active: boolean; color: string; critical?: boolean;
}) {
  return (
    <div
      className={`dash-threat-card ${active ? 'active' : ''} ${critical && active ? 'critical' : ''}`}
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
}

// ── Threat section with cards ────────────────────────────────
function ThreatSection({ title, color, threats }: { title: string; color: string; threats: ThreatItem[] }) {
  return (
    <div className="avia-section">
      <div className="avia-section-title" style={{ color }}>
        <span>▸</span> {title}
      </div>
      {threats.map((t, i) => {
        const emoji = THREAT_EMOJI[t.type] || '⚠️';
        const name = THREAT_NAMES[t.type] || t.type;
        const time = fmtTime(t.date);
        return (
          <div key={t.id || i} className="avia-card">
            <div className="avia-card-icon" style={{ background: `${color}18` }}>
              {emoji}
            </div>
            <div className="avia-card-body">
              <div className="avia-card-title">{t.place || t.region || 'Невідомо'}</div>
              <div className="avia-card-sub">
                {name}
                {t.course_direction && ` → ${t.course_direction}`}
                {t.speed_kmh ? ` (${t.speed_kmh} км/г)` : ''}
              </div>
              {t.text && <div className="avia-card-sub" style={{ opacity: 0.6 }}>{t.text}</div>}
            </div>
            {time && <span className="avia-card-time">{time}</span>}
          </div>
        );
      })}
    </div>
  );
}
