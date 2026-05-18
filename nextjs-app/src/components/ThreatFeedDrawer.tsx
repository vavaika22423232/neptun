'use client';

import { useState, useRef, useEffect, useMemo } from 'react';
import type { Marker } from '@/types';
import { THREAT_NAMES } from '@/types';
import { getLastActivityMs } from '@/lib/marker-activity';

interface ThreatFeedDrawerProps {
  markers: Marker[];
  isOpen: boolean;
  onClose: () => void;
}

const THREAT_COLOR: Record<string, string> = {
  ballistic: '#dc143c',
  missile: '#ff2a5f',
  raketa: '#ff2a5f',
  krylata: '#ff2a5f',
  pusk: '#ff2a5f',
  kab: '#ffd600',
  rszv: '#ffd600',
  shahed: '#ff6b35',
  drone: '#ff6b35',
  uav: '#ff6b35',
  fpv: '#f97316',
  rozved: '#4fc3f7',
  recon: '#4fc3f7',
  explosion: '#ff8c00',
  vibuh: '#ff8c00',
  artillery: '#a78bfa',
  obstril: '#a78bfa',
};

function threatColor(type: string): string {
  return THREAT_COLOR[type] || '#94a3b8';
}

function formatAgo(ms: number): string {
  const now = Date.now();
  if (ms <= 0) return '—';
  const s = Math.floor((now - ms) / 1000);
  if (s < 60) return `${s}с`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}хв`;
  return `${Math.floor(m / 60)}год`;
}

export default function ThreatFeedDrawer({ markers, isOpen, onClose }: ThreatFeedDrawerProps) {
  const drawerRef = useRef<HTMLDivElement>(null);
  const [_, setTick] = useState(0);

  // Refresh relative timestamps every 30s
  useEffect(() => {
    if (!isOpen) return;
    const iv = setInterval(() => setTick(t => t + 1), 30_000);
    return () => clearInterval(iv);
  }, [isOpen]);

  // Close on Escape
  useEffect(() => {
    if (!isOpen) return;
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [isOpen, onClose]);

  // Lock body scroll when open
  useEffect(() => {
    if (!isOpen) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = prev; };
  }, [isOpen]);

  const feed = useMemo(() => {
    const SKIP = new Set(['alarm', 'alarm_cancel', 'info', 'allclear', 'alert']);
    return [...markers]
      .filter(m => !SKIP.has(m.threat_type || ''))
      .sort((a, b) => getLastActivityMs(b) - getLastActivityMs(a))
      .slice(0, 30);
  }, [markers]);

  return (
    <>
      {/* Backdrop */}
      {isOpen && (
        <div
          className="threat-drawer-backdrop"
          aria-hidden
          onClick={onClose}
        />
      )}

      {/* Drawer */}
      <div
        ref={drawerRef}
        role="dialog"
        aria-modal="true"
        aria-label="Стрічка загроз"
        className={`threat-drawer${isOpen ? ' threat-drawer--open' : ''}`}
      >
        {/* Handle */}
        <div className="threat-drawer__handle-bar" aria-hidden>
          <div className="threat-drawer__handle" />
        </div>

        {/* Header */}
        <div className="threat-drawer__header">
          <div className="threat-drawer__header-title">
            <span className="threat-drawer__live-dot" aria-hidden />
            <span>Стрічка загроз</span>
          </div>
          <span className="threat-drawer__count-badge">{feed.length}</span>
          <button
            type="button"
            className="threat-drawer__close"
            aria-label="Закрити стрічку"
            onClick={onClose}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" width="16" height="16" aria-hidden>
              <path d="M18 6 6 18M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Feed list */}
        <div className="threat-drawer__list scrollbar-none">
          {feed.length === 0 ? (
            <div className="threat-drawer__empty">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" width="32" height="32" aria-hidden>
                <path d="M12 22c5.52 0 10-4.48 10-10S17.52 2 12 2 2 6.48 2 12s4.48 10 10 10z" />
                <path d="M12 8v4M12 16h.01" strokeWidth="2" />
              </svg>
              <span>Повітряний простір чистий</span>
            </div>
          ) : feed.map((m) => {
            const t = m.threat_type || 'default';
            const color = threatColor(t);
            const ts = getLastActivityMs(m);
            const count = Number(m.count) > 1 ? Number(m.count) : null;
            const place = [m.place, m.region].filter(Boolean).join(' · ') || null;
            return (
              <div key={`${m.track_id || m.id || ''}_${m.lat}_${m.lng}`} className="flex items-start gap-3 px-4 py-3 transition-colors hover:bg-[var(--hud-hover)] border-b border-[color:var(--hud-divider)] last:border-0">
                <div
                  className="mt-1.5 h-2 w-2 shrink-0 rounded-full"
                  style={{ background: color, boxShadow: `0 0 8px ${color}60` }}
                  aria-hidden
                />
                <div className="flex min-w-0 flex-1 flex-col gap-1">
                  <div className="flex items-baseline justify-between gap-2">
                    <div className="flex items-center gap-1.5 text-[13px] font-semibold" style={{ color }}>
                      {THREAT_NAMES[t] || t}
                      {count && (
                        <span className="rounded-full bg-[var(--hud-danger-bg)] px-1.5 py-0.5 text-[10px] font-bold text-[var(--hud-danger)] border border-[color:var(--hud-danger)]/20">
                          ×{count}
                        </span>
                      )}
                    </div>
                    <span className="shrink-0 text-[11px] font-medium tabular-nums text-[var(--hud-muted)]">
                      {formatAgo(ts)}
                    </span>
                  </div>
                  {place && (
                    <div className="truncate text-[11.5px] text-[var(--hud-muted)]">
                      {place}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </>
  );
}
