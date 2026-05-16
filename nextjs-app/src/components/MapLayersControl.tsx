'use client';

import { useState, useRef, useEffect } from 'react';
import type { MapBasemapKind } from '@/lib/map-leaflet-performance';

interface MapLayersControlProps {
  basemap: MapBasemapKind;
  onChange: (b: MapBasemapKind) => void;
}

const LAYERS: { value: MapBasemapKind; label: string; icon: React.ReactNode }[] = [
  {
    value: 'rasterVectorDark',
    label: 'Тактична (Темна)',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" className="h-4 w-4" aria-hidden>
        <path d="M12 2L2 7l10 5 10-5-10-5z" fill="currentColor" opacity="0.9" />
        <path d="M2 17l10 5 10-5M2 12l10 5 10-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" opacity="0.5" />
      </svg>
    ),
  },
  {
    value: 'googleHybrid',
    label: 'Супутник (Google)',
    icon: (
      <svg viewBox="0 0 24 24" fill="none" className="h-4 w-4" aria-hidden>
        <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" />
        <path d="M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10 15.3 15.3 0 01-4-10 15.3 15.3 0 014-10z" stroke="currentColor" strokeWidth="2" />
        <path d="M2 12h20" stroke="currentColor" strokeWidth="2" />
      </svg>
    ),
  },
];

export default function MapLayersControl({ basemap, onChange }: MapLayersControlProps) {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const activeLayer = LAYERS.find(l => l.value === basemap) || LAYERS[0];

  return (
    <div className="relative" ref={containerRef}>
      {/* Trigger Button */}
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className="flex h-11 w-11 items-center justify-center rounded-[12px] border border-[color:var(--hud-border)] bg-[var(--hud-surface)] text-[var(--hud-text)] shadow-[var(--hud-shadow)] backdrop-blur-xl transition-all hover:bg-[var(--hud-hover)] active:scale-95 sm:h-10 sm:w-10 sm:rounded-[14px]"
        aria-label="Змінити шар карти"
        title="Шари карти"
      >
        <svg viewBox="0 0 24 24" fill="none" className="h-[18px] w-[18px]" aria-hidden>
          <path d="M12 2L2 7l10 5 10-5-10-5z" fill="currentColor" />
          <path d="M2 17l10 5 10-5M2 12l10 5 10-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </button>

      {/* Dropdown Menu */}
      {open && (
        <div className="absolute right-0 top-full mt-2 w-56 origin-top-right overflow-hidden rounded-[16px] border border-[color:var(--hud-border)] bg-[var(--hud-surface-strong)] p-1 shadow-2xl backdrop-blur-2xl animate-in fade-in zoom-in-95">
          <div className="mb-1 px-3 pt-2 text-[10px] font-bold tracking-wider text-[var(--hud-muted)]">
            БАЛАНС КАРТИ
          </div>
          {LAYERS.map((layer) => (
            <button
              key={layer.value}
              type="button"
              onClick={() => {
                onChange(layer.value);
                setOpen(false);
              }}
              className="flex w-full items-center justify-between gap-3 rounded-[10px] px-3 py-2.5 text-left text-[13px] font-medium transition-colors hover:bg-[var(--hud-hover)]"
              style={{
                color: basemap === layer.value ? '#38bdf8' : 'var(--hud-text)',
                backgroundColor: basemap === layer.value ? 'rgba(56, 189, 248, 0.1)' : 'transparent',
              }}
            >
              <span className="flex items-center gap-3">
                <span style={{ color: basemap === layer.value ? '#38bdf8' : 'var(--hud-muted)' }}>
                  {layer.icon}
                </span>
                {layer.label}
              </span>
              {basemap === layer.value && (
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" className="h-3.5 w-3.5">
                  <path d="M20 6L9 17l-5-5" />
                </svg>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
