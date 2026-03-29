import type { AlarmColorPreset } from '@/contexts/MapPreferencesContext';

/** CSS variables on :root for SVG oblast / district overlays (desktop). */
export function applyAlarmCssVariables(
  preset: AlarmColorPreset,
  opacityMul: number,
): void {
  if (typeof document === 'undefined') return;
  const root = document.documentElement;
  const o = Math.min(1, Math.max(0.35, opacityMul));

  const clear = (name: string) => root.style.removeProperty(name);

  if (preset === 'default') {
    clear('--alarm-state-fill');
    clear('--alarm-state-stroke');
    clear('--alarm-district-fill');
    clear('--alarm-district-stroke');
    clear('--alarm-pulse-a');
    clear('--alarm-pulse-b');
    root.style.setProperty('--alarm-fill-opacity-mul', String(o));
    return;
  }

  const table: Record<
    Exclude<AlarmColorPreset, 'default'>,
    { sf: string; ss: string; df: string; ds: string; pa: string; pb: string }
  > = {
    ember: {
      sf: '#7c2d12',
      ss: '#fb923c',
      df: '#c2410c',
      ds: '#fdba74',
      pa: '#7c2d12',
      pb: '#431407',
    },
    rose: {
      sf: '#881337',
      ss: '#fb7185',
      df: '#be123c',
      ds: '#fda4af',
      pa: '#881337',
      pb: '#4c0519',
    },
    violet: {
      sf: '#5b21b6',
      ss: '#a78bfa',
      df: '#6d28d9',
      ds: '#c4b5fd',
      pa: '#5b21b6',
      pb: '#2e1065',
    },
  };

  const c = table[preset];
  root.style.setProperty('--alarm-state-fill', c.sf);
  root.style.setProperty('--alarm-state-stroke', c.ss);
  root.style.setProperty('--alarm-district-fill', c.df);
  root.style.setProperty('--alarm-district-stroke', c.ds);
  root.style.setProperty('--alarm-pulse-a', c.pa);
  root.style.setProperty('--alarm-pulse-b', c.pb);
  root.style.setProperty('--alarm-fill-opacity-mul', String(o));
}

/** Leaflet GeoJSON path style (embed / fallback). */
export function geoJsonAlarmStyle(
  preset: AlarmColorPreset,
  opacityMul: number,
  lightTheme: boolean,
): { fillColor: string; fillOpacity: number; color: string; weight: number } {
  const o = Math.min(1, Math.max(0.35, opacityMul));
  const fillOpacity = 0.55 + 0.4 * o;

  if (preset === 'default') {
    return {
      fillColor: '#dc2626',
      fillOpacity: fillOpacity * 0.95,
      color: lightTheme ? '#b91c1c' : '#ff6b6b',
      weight: 0.8,
    };
  }
  const t = {
    ember: { fillColor: '#ea580c', color: '#fdba74' },
    rose: { fillColor: '#e11d48', color: '#fda4af' },
    violet: { fillColor: '#7c3aed', color: '#c4b5fd' },
  }[preset];
  return { fillColor: t.fillColor, fillOpacity, color: t.color, weight: 0.85 };
}
