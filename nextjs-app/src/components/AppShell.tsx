'use client';

import React, { useMemo, useState, useEffect, type ReactNode } from 'react';
import type { Marker, Alarm, BallisticThreat, PresenceData } from '@/types';
import type { MapBasemapKind } from '@/lib/map-leaflet-performance';
import { UNITED24_DONATE_URL, COME_BACK_ALIVE_DONATE_URL, TELEGRAM_CHANNEL_URL } from '@/lib/constants';
import BottomBar from './BottomBar';
import ThreatFeedDrawer from './ThreatFeedDrawer';
import MapLayersControl from './MapLayersControl';

interface AppShellProps {
  markers: Marker[];
  alarms: Alarm[];
  presence: PresenceData;
  ballisticThreat: BallisticThreat | null;
  onDonate: () => void;
  onFaq: () => void;
  onToggleUkraineOnly: () => void;
  ukraineOnly: boolean;
  basemap?: MapBasemapKind;
  onBasemapChange?: (b: MapBasemapKind) => void;
  trackingActive?: boolean;
  onToggleTracking?: () => void;
  lastUpdateMs?: number;
  children: React.ReactNode;
}

const MENU_ITEMS = [
  {
    id: 'faq',
    label: 'Довідка',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4 shrink-0" aria-hidden>
        <circle cx="12" cy="12" r="9" /><path d="M12 8h.01M11 12h1v5h1" />
      </svg>
    ),
  },
  {
    id: 'donate',
    label: 'Підтримати',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4 shrink-0" aria-hidden>
        <path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.6l-1-1a5.5 5.5 0 0 0-7.8 7.8l1 1L12 21l7.8-7.6 1-1a5.5 5.5 0 0 0 0-7.8Z" />
      </svg>
    ),
  },
];

const itemCls =
  'flex w-full items-center gap-3 rounded-[12px] px-3 py-2.5 text-[13px] font-semibold text-[var(--hud-text)] transition-colors hover:bg-[var(--hud-hover)] active:bg-[var(--hud-active)]';

const telegramIconPath =
  'M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 5.42-1.13 7.19-.14.75-.42 1-.68 1.03-.58.05-1.02-.38-1.58-.75-.88-.58-1.38-.94-2.23-1.5-.99-.65-.35-1.01.22-1.59.15-.15 2.71-2.48 2.76-2.69a.2.2 0 00-.05-.18c-.06-.05-.14-.03-.21-.02-.09.02-1.49.95-4.22 2.79-.4.27-.76.41-1.08.4-.36-.01-1.04-.2-1.55-.37-.63-.2-1.12-.31-1.08-.66.02-.18.27-.36.74-.55 2.92-1.27 4.86-2.11 5.83-2.51 2.78-1.16 3.35-1.36 3.73-1.36.08 0 .27.02.39.12.1.08.13.19.14.27-.01.06.01.24 0 .38z';

function runThemeToggle() {
  const root = document.documentElement;
  const themeColor = document.querySelector('meta[name="theme-color"]');
  if (root.classList.contains('dark')) {
    root.classList.remove('dark');
    root.classList.add('theme-light');
    root.style.colorScheme = 'light';
    themeColor?.setAttribute('content', '#f5f7fa');
    localStorage.setItem('theme', 'light');
  } else {
    root.classList.remove('theme-light');
    root.classList.add('dark');
    root.style.colorScheme = 'dark';
    themeColor?.setAttribute('content', '#0a0a0b');
    localStorage.setItem('theme', 'dark');
  }
  window.dispatchEvent(new Event('theme-change'));
}

function IconSvg({ children, strokeWidth = 2.35 }: { children: ReactNode; strokeWidth?: number }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      className="h-[18px] w-[18px]"
      aria-hidden
    >
      {children}
    </svg>
  );
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
  basemap,
  onBasemapChange,
  trackingActive,
  onToggleTracking,
  lastUpdateMs,
  children,
}: AppShellProps) {
  const activeAlarms = useMemo(() => alarms.filter(a => a.activeAlerts?.length > 0).length, [alarms]);
  void ballisticThreat;
  const [feedOpen, setFeedOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [isDarkTheme, setIsDarkTheme] = useState(false);

  useEffect(() => {
    const syncTheme = () => setIsDarkTheme(document.documentElement.classList.contains('dark'));
    syncTheme();
    window.addEventListener('theme-change', syncTheme);
    return () => window.removeEventListener('theme-change', syncTheme);
  }, []);

  useEffect(() => {
    if (!menuOpen) return;
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = prevOverflow;
    };
  }, [menuOpen]);

  useEffect(() => {
    if (!menuOpen) return;
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') setMenuOpen(false); };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, [menuOpen]);

  const close = () => setMenuOpen(false);

  return (
    <div className="relative h-[100dvh] w-full overflow-hidden font-sans text-[var(--on-surface)] selection:bg-[#ff2a5f]/30 transition-colors duration-300">

      {/* Maintenance Notice centralized in RootLayout */}

      {/* Map */}
      <main className="absolute inset-0 z-0">{children}</main>

      {/* Threat Feed Drawer */}
      <ThreatFeedDrawer
        markers={markers}
        isOpen={feedOpen}
        onClose={() => setFeedOpen(false)}
      />

      {/* HUD layer */}
      <div className="pointer-events-none absolute inset-0 z-[2000]">
        
        {/* Top row: Telegram + Lock-on + Layers + Menu */}
        <div className="pointer-events-auto absolute inset-x-3 top-[calc(env(safe-area-inset-top,0px)+0.5rem)] z-[2460] flex items-stretch justify-end gap-2 sm:right-4 sm:top-4 sm:left-auto sm:w-fit">
          
          {/* ── Telegram CTA ─────────────────────────────── */}
          <a
            href={TELEGRAM_CHANNEL_URL}
            target="_blank"
            rel="noopener noreferrer"
            aria-label="Telegram-канал NEPTUN"
            title="Telegram-канал NEPTUN"
            className="flex h-11 shrink-0 items-center gap-2 rounded-full border border-[color:var(--hud-border)] bg-[#0088cc] px-4 text-white shadow-[var(--hud-shadow)] backdrop-blur-2xl transition-all hover:bg-[#0099e6] hover:scale-[1.03] active:scale-[0.98] sm:h-10"
          >
            <svg viewBox="0 0 24 24" className="h-[18px] w-[18px] shrink-0" fill="currentColor" aria-hidden>
              <path d={telegramIconPath} />
            </svg>
            <span className="hidden text-[12px] font-bold tracking-tight lg:inline">ХЛОПЦІ ПИШУТЬ В TELEGRAM</span>
            <span className="text-[12px] font-bold tracking-tight lg:hidden">TELEGRAM</span>
          </a>

          {/* ── Tracking Lock-on ─────────────────────── */}
          {onToggleTracking && markers.length > 0 && (
            <button
              type="button"
              onClick={onToggleTracking}
              className={`flex h-11 shrink-0 items-center gap-2 rounded-full border border-[color:var(--hud-border)] px-4 text-[12px] font-bold tracking-tight shadow-[var(--hud-shadow)] backdrop-blur-2xl transition-all active:scale-95 sm:h-10 ${
                trackingActive 
                  ? 'bg-[var(--hud-danger-bg)] text-[var(--hud-danger)] ring-1 ring-[var(--hud-danger)]/50 hover:bg-[var(--hud-danger-bg)]/80' 
                  : 'bg-[var(--hud-surface)] text-[var(--hud-text)] hover:bg-[var(--hud-hover)]'
              }`}
              title={trackingActive ? 'Вимкнути слідкування' : 'Увімкнути слідкування за ціллю'}
            >
              <div className="relative flex items-center justify-center">
                <svg viewBox="0 0 24 24" fill="none" className={`h-4 w-4 ${trackingActive ? 'animate-pulse' : ''}`} aria-hidden>
                  <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="2" />
                  <circle cx="12" cy="12" r="3" fill={trackingActive ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth="1.5" />
                  <path d="M12 3v3M12 18v3M3 12h3M18 12h3" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                </svg>
              </div>
              <span className="hidden sm:inline">{trackingActive ? 'СЛІДКУЮ' : 'СЛІДКУВАТИ'}</span>
              {!trackingActive && <span className="sm:hidden">LOCK</span>}
              {trackingActive && <span className="sm:hidden">ON</span>}
            </button>
          )}

          {basemap && onBasemapChange && (
            <MapLayersControl
              basemap={basemap}
              onChange={onBasemapChange}
            />
          )}

          <button
            type="button"
            aria-label="Меню"
            aria-expanded={menuOpen}
            aria-controls="neptun-hud-drawer"
            onClick={() => setMenuOpen(v => !v)}
            className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full border border-[color:var(--hud-border)] bg-[var(--hud-surface)] text-[var(--hud-text)] shadow-[var(--hud-shadow)] backdrop-blur-2xl transition-colors hover:bg-[var(--hud-hover)] active:bg-[var(--hud-active)] sm:h-10 sm:w-10"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" className="h-4 w-4" aria-hidden>
              {menuOpen ? (
                <path d="M18 6 6 18M6 6l12 12" />
              ) : (
                <path d="M4 6h16M4 12h16M4 18h16" />
              )}
            </svg>
          </button>
        </div>

        {menuOpen ? (
          <>
            <div
              className="pointer-events-auto fixed inset-0 z-[2440] bg-black/45 backdrop-blur-[2px]"
              aria-hidden
              onClick={close}
              onKeyDown={(e) => { if (e.key === 'Escape') close(); }}
            />

            <aside
              id="neptun-hud-drawer"
              role="dialog"
              aria-modal="true"
              aria-labelledby="neptun-drawer-title"
              className="pointer-events-auto fixed right-0 top-0 z-[2450] flex h-[100dvh] w-[min(21rem,calc(100vw-12px))] flex-col overflow-hidden rounded-l-[22px] border-l border-[color:var(--hud-border)] bg-[var(--hud-surface-strong)] pb-[calc(env(safe-area-inset-bottom,0px)+12px)] pl-px pt-[calc(env(safe-area-inset-top,0px)+8px)] shadow-[var(--hud-modal-shadow)] backdrop-blur-2xl"
            >
              <div className="flex shrink-0 items-center gap-3 border-b border-[color:var(--hud-border)] px-4 pb-3 pt-2">
                <div className="flex h-9 items-center gap-2.5 rounded-[14px] bg-[var(--hud-chip)] px-3">
                  <span className="text-[11px] font-black uppercase tracking-[0.14em] text-[var(--hud-text)]">NEPTUN</span>
                  <span className="h-4 w-px bg-[var(--hud-divider)]" aria-hidden />
                  <span className="h-5 w-5 overflow-hidden rounded-full shadow-[0_0_0_1px_var(--hud-border)]" title="Україна" aria-hidden>
                    <span className="block h-1/2 bg-[#198de5]" />
                    <span className="block h-1/2 bg-[#ffd43b]" />
                  </span>
                </div>
                <h2 id="neptun-drawer-title" className="flex-1 text-[14px] font-bold tracking-tight text-[var(--hud-text)]">
                  Навігація
                </h2>
              </div>

              <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-4 pt-3">
                <div className="flex flex-col gap-0.5">
                  <button
                    type="button"
                    onClick={(e) => { e.preventDefault(); onToggleUkraineOnly(); }}
                    className={`${itemCls} ${ukraineOnly ? 'bg-[var(--hud-hover)]' : ''}`}
                    aria-label={ukraineOnly ? 'Показати сусідні країни' : 'Показати тільки Україну'}
                    aria-pressed={ukraineOnly}
                  >
                    <span className="text-[var(--hud-muted)]">
                      <IconSvg strokeWidth={2.15}>
                        <path d="M4 6.5 12 3l8 3.5v11L12 21l-8-3.5z" /><path d="M12 3v18M4 6.5l8 4 8-4" />
                      </IconSvg>
                    </span>
                    <span className="min-w-0">
                      {ukraineOnly ? 'Показати сусідні країни' : 'Тільки Україна'}
                    </span>
                  </button>
                  <button
                    type="button"
                    onClick={runThemeToggle}
                    className={itemCls}
                    aria-label={isDarkTheme ? 'Увімкнути світлу тему' : 'Увімкнути темну тему'}
                  >
                    <span className="text-[var(--hud-muted)]">
                      <IconSvg strokeWidth={2.2}>
                        {isDarkTheme ? (
                          <>
                            <circle cx="12" cy="12" r="4" />
                            <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2M4.93 19.07l1.41-1.41M17.66 6.34l1.41-1.41" />
                          </>
                        ) : (
                          <path d="M21 12.8A8.5 8.5 0 1 1 11.2 3a6.5 6.5 0 0 0 9.8 9.8Z" />
                        )}
                      </IconSvg>
                    </span>
                    {isDarkTheme ? 'Світла тема' : 'Темна тема'}
                  </button>
                  {MENU_ITEMS.map(item => (
                    <button
                      key={item.id}
                      type="button"
                      onClick={() => {
                        close();
                        if (item.id === 'faq') onFaq();
                        if (item.id === 'donate') onDonate();
                      }}
                      className={itemCls}
                    >
                      <span className="text-[var(--hud-muted)]">{item.icon}</span>
                      {item.label}
                    </button>
                  ))}
                </div>

                <div className="mx-0 my-4 h-px bg-[var(--hud-divider)]" />

                <p className="px-0.5 pb-2 pt-0 text-[10px] font-black uppercase tracking-[0.2em] text-[var(--hud-muted)]">Підтримай Україну</p>

                <a
                  href={UNITED24_DONATE_URL}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={close}
                  className="mb-1 flex items-center gap-3 rounded-[12px] px-2 py-2 transition-colors hover:bg-[var(--hud-hover)] active:bg-[var(--hud-active)]"
                >
                  <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-[7px] bg-[#005BBB]">
                    <svg viewBox="0 0 20 20" className="h-3.5 w-3.5" fill="none" aria-hidden>
                      <circle cx="10" cy="10" r="8" fill="#FFD700" />
                      <circle cx="10" cy="10" r="5" fill="#005BBB" />
                      <circle cx="10" cy="10" r="2.5" fill="#FFD700" />
                    </svg>
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-[12px] font-bold leading-tight text-[var(--hud-text)]">United24</p>
                    <p className="text-[10px] leading-tight text-[var(--hud-muted)]">Офіційна збірна України</p>
                  </div>
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-3.5 w-3.5 shrink-0 text-[var(--hud-muted)]" aria-hidden>
                    <path d="M7 17 17 7M7 7h10v10" />
                  </svg>
                </a>

                <a
                  href={COME_BACK_ALIVE_DONATE_URL}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={close}
                  className="flex items-center gap-3 rounded-[12px] px-2 py-2 pb-1 transition-colors hover:bg-[var(--hud-hover)] active:bg-[var(--hud-active)]"
                >
                  <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-[7px] bg-[#1a1a1a]">
                    <svg viewBox="0 0 20 20" className="h-3.5 w-3.5" fill="none" aria-hidden>
                      <path d="M10 16s-7-4.5-7-8.5A4 4 0 0 1 10 5.27 4 4 0 0 1 17 7.5C17 11.5 10 16 10 16z" fill="#e8363d" />
                    </svg>
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-[12px] font-bold leading-tight text-[var(--hud-text)]">Повернись живим</p>
                    <p className="text-[10px] leading-tight text-[var(--hud-muted)]">Фонд підтримки армії</p>
                  </div>
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="h-3.5 w-3.5 shrink-0 text-[var(--hud-muted)]" aria-hidden>
                    <path d="M7 17 17 7M7 7h10v10" />
                  </svg>
                </a>
              </div>
            </aside>
          </>
        ) : null}

        <BottomBar
          activeAlarms={activeAlarms}
          targetsCount={markers.length}
          onlineCount={presence.total ?? 0}
          onOpenFeed={() => setFeedOpen(true)}
          lastUpdateMs={lastUpdateMs}
        />
      </div>
    </div>
  );
}
