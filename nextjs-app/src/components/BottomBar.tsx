'use client';

import Link from 'next/link';
import { useId, useState, useEffect, useRef } from 'react';
import { BottomBarAppRibbonStripe } from '@/components/BottomBarAppRibbon';

export interface BottomBarStatsProps {
  activeAlarms: number;
  targetsCount: number;
  onlineCount: number;
  onOpenFeed?: () => void;
  lastUpdateMs?: number;
}

function UaRoundelFlag({ className }: { className?: string }) {
  const uid = useId().replace(/[^a-zA-Z0-9]/g, '');
  const clipId = `ua-flag-${uid}`;
  return (
    <svg viewBox="0 0 24 24" className={className} aria-hidden>
      <defs>
        <clipPath id={clipId}>
          <circle cx="12" cy="12" r="11" />
        </clipPath>
      </defs>
      <g clipPath={`url(#${clipId})`}>
        <rect x="1" y="1" width="22" height="11" fill="#0057b7" />
        <rect x="1" y="12" width="22" height="11" fill="#ffd700" />
      </g>
    </svg>
  );
}

function formatLastUpdate(ms: number | undefined): string {
  if (!ms || ms <= 0) return '';
  const s = Math.floor((Date.now() - ms) / 1000);
  if (s < 10) return 'щойно';
  if (s < 60) return `${s}с тому`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}хв тому`;
  return `${Math.floor(m / 60)}год тому`;
}

/** Compact single-row Tactical HUD strip */
function TacticalHudStrip({ activeAlarms, targetsCount, onlineCount, onOpenFeed, lastUpdateMs }: BottomBarStatsProps) {
  const [updateLabel, setUpdateLabel] = useState('');
  const tickRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    setUpdateLabel(formatLastUpdate(lastUpdateMs));
    tickRef.current = setInterval(() => {
      setUpdateLabel(formatLastUpdate(lastUpdateMs));
    }, 15_000);
    return () => { if (tickRef.current) clearInterval(tickRef.current); };
  }, [lastUpdateMs]);

  return (
    <div
      className="tactical-hud-strip"
      role="group"
      aria-label="Живий статус NEPTUN"
    >
      {/* Logo segment */}
      <Link
        href="/"
        prefetch={false}
        className="tactical-hud-segment tactical-hud-segment--logo"
        title="На головну NEPTUN"
        aria-label="На головну NEPTUN"
      >
        <span className="tactical-hud-brand">NEPTUN</span>
        <UaRoundelFlag className="h-[18px] w-[18px] shrink-0 rounded-full" />
      </Link>

      <div className="tactical-hud-divider" aria-hidden />

      {/* Alarms segment */}
      <div
        className={`tactical-hud-segment${activeAlarms > 0 ? ' tactical-hud-segment--alarm' : ''}`}
        title="Активні тривоги"
        aria-label={`Активні тривоги: ${activeAlarms}`}
      >
        <span className="tactical-hud-dot-wrap" aria-hidden>
          {activeAlarms > 0 && (
            <span className="tactical-hud-ping" />
          )}
          <span className={`tactical-hud-dot${activeAlarms > 0 ? ' tactical-hud-dot--alarm' : ' tactical-hud-dot--ok'}`} />
        </span>
        <span className="tactical-hud-stat-label">Тривоги</span>
        <span className={`tactical-hud-stat-value${activeAlarms > 0 ? ' tactical-hud-stat-value--alarm' : ' tactical-hud-stat-value--muted'}`}>
          {activeAlarms}
        </span>
      </div>

      <div className="tactical-hud-divider" aria-hidden />

      {/* Targets segment — tappable → opens feed */}
      <button
        type="button"
        className="tactical-hud-segment tactical-hud-segment--btn"
        title="Активні цілі — відкрити стрічку"
        aria-label={`Активні цілі: ${targetsCount}. Натисніть щоб відкрити стрічку`}
        onClick={onOpenFeed}
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.2} strokeLinecap="round" strokeLinejoin="round" className="tactical-hud-icon" aria-hidden>
          <circle cx="12" cy="12" r="2.5" />
          <path d="M12 4v3M12 17v3M4 12h3M17 12h3" />
        </svg>
        <span className="tactical-hud-stat-label">Цілі</span>
        <span className="tactical-hud-stat-value">{targetsCount}</span>
        {targetsCount > 0 && (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" className="tactical-hud-chevron" aria-hidden>
            <path d="m18 15-6-6-6 6" />
          </svg>
        )}
      </button>

      <div className="tactical-hud-divider" aria-hidden />

      {/* Online segment */}
      <div
        className="tactical-hud-segment"
        title="Онлайн"
        aria-label={`Онлайн: ${onlineCount}`}
      >
        <span className="tactical-hud-dot tactical-hud-dot--online" aria-hidden />
        <span className="tactical-hud-stat-label tactical-hud-stat-label--sm">Онлайн</span>
        <span className="tactical-hud-stat-value">{onlineCount}</span>
      </div>

      {/* Update timestamp — only on wider screens */}
      {updateLabel && (
        <>
          <div className="tactical-hud-divider tactical-hud-divider--wide" aria-hidden />
          <div className="tactical-hud-segment tactical-hud-segment--update" aria-label={`Оновлено: ${updateLabel}`}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" className="tactical-hud-icon tactical-hud-icon--sm" aria-hidden>
              <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
              <path d="M3 3v5h5M12 7v5l4 2" />
            </svg>
            <span className="tactical-hud-update-label">{updateLabel}</span>
          </div>
        </>
      )}
    </div>
  );
}

export default function BottomBar({ activeAlarms, targetsCount, onlineCount, onOpenFeed, lastUpdateMs }: BottomBarStatsProps) {
  return (
    <nav
      className="bottom-bar"
      aria-label="Статус карти та застосунок"
    >
      {/* App ribbon — collapsed to one smart row */}
      <div className="bottom-bar__ribbon">
        <div className="sm:hidden">
          <BottomBarAppRibbonStripe slot="bottom_strip_mobile" />
        </div>
        <div className="hidden sm:block">
          <BottomBarAppRibbonStripe slot="bottom_strip_desktop" />
        </div>
      </div>

      {/* Tactical HUD strip */}
      <TacticalHudStrip
        activeAlarms={activeAlarms}
        targetsCount={targetsCount}
        onlineCount={onlineCount}
        onOpenFeed={onOpenFeed}
        lastUpdateMs={lastUpdateMs}
      />
    </nav>
  );
}
