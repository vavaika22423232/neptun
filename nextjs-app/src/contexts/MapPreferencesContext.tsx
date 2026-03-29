'use client';

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react';

export type MapBaseType = 'vector' | 'satellite';
export type AlarmColorPreset = 'default' | 'ember' | 'rose' | 'violet';

const STORAGE_KEY = 'neptun_map_prefs_v1';

interface Stored {
  mapType?: MapBaseType;
  markerScale?: number;
  alarmPreset?: AlarmColorPreset;
  alarmOpacity?: number;
}

interface MapPreferencesValue {
  mapType: MapBaseType;
  setMapType: (t: MapBaseType) => void;
  markerScale: number;
  setMarkerScale: (n: number) => void;
  alarmPreset: AlarmColorPreset;
  setAlarmPreset: (p: AlarmColorPreset) => void;
  alarmOpacity: number;
  setAlarmOpacity: (n: number) => void;
}

const defaultValue: MapPreferencesValue = {
  mapType: 'vector',
  setMapType: () => {},
  markerScale: 1,
  setMarkerScale: () => {},
  alarmPreset: 'default',
  setAlarmPreset: () => {},
  alarmOpacity: 1,
  setAlarmOpacity: () => {},
};

const MapPreferencesContext = createContext<MapPreferencesValue>(defaultValue);

function clamp(n: number, min: number, max: number) {
  return Math.min(max, Math.max(min, n));
}

export function MapPreferencesProvider({ children }: { children: React.ReactNode }) {
  const [mapType, setMapTypeState] = useState<MapBaseType>('vector');
  const [markerScale, setMarkerScaleState] = useState(1);
  const [alarmPreset, setAlarmPresetState] = useState<AlarmColorPreset>('default');
  const [alarmOpacity, setAlarmOpacityState] = useState(1);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const p = JSON.parse(raw) as Stored;
        if (p.mapType === 'vector' || p.mapType === 'satellite') setMapTypeState(p.mapType);
        if (typeof p.markerScale === 'number' && p.markerScale >= 0.7 && p.markerScale <= 1.45) {
          setMarkerScaleState(p.markerScale);
        }
        if (p.alarmPreset && ['default', 'ember', 'rose', 'violet'].includes(p.alarmPreset)) {
          setAlarmPresetState(p.alarmPreset);
        }
        if (typeof p.alarmOpacity === 'number' && p.alarmOpacity >= 0.35 && p.alarmOpacity <= 1) {
          setAlarmOpacityState(p.alarmOpacity);
        }
      }
    } catch {
      /* ignore */
    }
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (!hydrated) return;
    try {
      const payload: Stored = {
        mapType,
        markerScale,
        alarmPreset,
        alarmOpacity,
      };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
    } catch {
      /* ignore */
    }
  }, [hydrated, mapType, markerScale, alarmPreset, alarmOpacity]);

  const setMapType = useCallback((t: MapBaseType) => setMapTypeState(t), []);
  const setMarkerScale = useCallback((n: number) => {
    setMarkerScaleState(clamp(n, 0.7, 1.45));
  }, []);
  const setAlarmPreset = useCallback((p: AlarmColorPreset) => setAlarmPresetState(p), []);
  const setAlarmOpacity = useCallback((n: number) => {
    setAlarmOpacityState(clamp(n, 0.35, 1));
  }, []);

  const value = useMemo<MapPreferencesValue>(
    () => ({
      mapType,
      setMapType,
      markerScale,
      setMarkerScale,
      alarmPreset,
      setAlarmPreset,
      alarmOpacity,
      setAlarmOpacity,
    }),
    [mapType, setMapType, markerScale, setMarkerScale, alarmPreset, setAlarmPreset, alarmOpacity, setAlarmOpacity],
  );

  return <MapPreferencesContext.Provider value={value}>{children}</MapPreferencesContext.Provider>;
}

export function useMapPreferences() {
  return useContext(MapPreferencesContext);
}
