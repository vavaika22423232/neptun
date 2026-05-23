import { create } from 'zustand';
import type { MapAlarmData, MapMarkerData, ThreatMarker } from '../../../types/map';
import { applyMarkerPatch } from '../engine/applyMarkerPatch';
import { cancelMarkerMotion, scheduleMarkerMotion } from '../engine/applyTrackMotion';
import { markerKey, parseThreatMarker } from '../utils/parseThreatMarker';

type LinkPhase = 'idle' | 'connecting' | 'live' | 'reconnecting' | 'offline';

export type MapFocusPlace = {
  lat: number;
  lng: number;
  zoom?: number;
  duration?: number;
  label?: string;
  nonce: number;
};

type MapState = {
  alarms: MapAlarmData;
  markers: ThreatMarker[];
  counts: Record<string, number>;
  linkPhase: LinkPhase;
  lastSignificantRefreshAt?: number;
  lastUpdate?: number;
  visibleThreatTypes: Record<string, boolean>;
  showOblastAlarms: boolean;
  showTrajectories: boolean;
  layerSheetVisible: boolean;
  locateUserNonce: number;
  focusPlace?: MapFocusPlace;
  setAlarmData: (data: MapAlarmData) => void;
  setMarkerData: (data: MapMarkerData) => void;
  upsertMarker: (raw: unknown) => void;
  patchTrack: (raw: Record<string, unknown>) => void;
  deleteMarker: (id: string) => void;
  setLinkPhase: (phase: LinkPhase) => void;
  touchSignificantRefresh: () => void;
  toggleThreatType: (type: string) => void;
  toggleOblastAlarms: () => void;
  toggleTrajectories: () => void;
  setLayerSheetVisible: (visible: boolean) => void;
  requestLocateUser: () => void;
  requestFocusPlace: (place: Omit<MapFocusPlace, 'nonce'>) => void;
};

const initialAlarms: MapAlarmData = {
  stateAlarms: {},
  districtAlarms: {},
  stateThreatTypes: {},
  stateCount: 0,
  districtCount: 0,
  ballisticRegions: [],
};

export const useMapStore = create<MapState>((set) => ({
  alarms: initialAlarms,
  markers: [],
  counts: {},
  linkPhase: 'idle',
  visibleThreatTypes: {
    shahed: true,
    raketa: true,
    kab: true,
    fpv: true,
    rszv: true,
    avia: true,
  },
  showOblastAlarms: true,
  showTrajectories: false,
  layerSheetVisible: false,
  locateUserNonce: 0,
  focusPlace: undefined,
  setAlarmData: (alarms) => set({ alarms, lastUpdate: Date.now() }),
  setMarkerData: (data) => set({ markers: data.markers, counts: data.counts, lastUpdate: Date.now() }),
  upsertMarker: (raw) =>
    set((state) => {
      const marker = parseThreatMarker(raw);
      if (!marker) return state;
      const key = markerKey(marker);
      const next = state.markers.filter((m) => markerKey(m) !== key);
      next.push(marker);
      return {
        markers: next,
        counts: next.reduce<Record<string, number>>((acc, m) => {
          acc[m.threatType] = (acc[m.threatType] ?? 0) + 1;
          return acc;
        }, {}),
        lastUpdate: Date.now(),
      };
    }),
  patchTrack: (raw) =>
    set((state) => {
      const payloadMarker = raw.marker;
      const parsed = parseThreatMarker(payloadMarker);
      const trackId = parsed?.trackId || String(raw.track_id ?? '');
      const updates =
        payloadMarker != null && typeof payloadMarker === 'object'
          ? (payloadMarker as Record<string, unknown>)
          : raw;
      const markers = state.markers.map((current) => {
        const same =
          (parsed?.id && current.id === parsed.id) ||
          (trackId && current.trackId === trackId) ||
          (parsed && markerKey(current) === markerKey(parsed));
        if (!same) return current;
        const next = applyMarkerPatch(current, updates);
        scheduleMarkerMotion(current, next);
        return next;
      });
      return { markers, lastUpdate: Date.now() };
    }),
  deleteMarker: (id) =>
    set((state) => {
      const removed = state.markers.filter((m) => m.id === id || m.trackId === id);
      for (const m of removed) {
        cancelMarkerMotion(markerKey(m));
      }
      const markers = state.markers.filter((m) => m.id !== id && m.trackId !== id);
      return { markers, lastUpdate: Date.now() };
    }),
  setLinkPhase: (phase) => set({ linkPhase: phase }),
  touchSignificantRefresh: () => set({ lastSignificantRefreshAt: Date.now() }),
  toggleThreatType: (type) =>
    set((state) => ({
      visibleThreatTypes: {
        ...state.visibleThreatTypes,
        [type]: !(state.visibleThreatTypes[type] ?? true),
      },
    })),
  toggleOblastAlarms: () => set((s) => ({ showOblastAlarms: !s.showOblastAlarms })),
  toggleTrajectories: () => set((s) => ({ showTrajectories: !s.showTrajectories })),
  setLayerSheetVisible: (visible) => set({ layerSheetVisible: visible }),
  requestLocateUser: () => set((s) => ({ locateUserNonce: s.locateUserNonce + 1 })),
  requestFocusPlace: (place) =>
    set((s) => ({
      focusPlace: {
        ...place,
        nonce: (s.focusPlace?.nonce ?? 0) + 1,
      },
    })),
}));
