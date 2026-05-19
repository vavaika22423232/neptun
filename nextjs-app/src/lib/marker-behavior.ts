import type { Marker } from '@/types';
import { MAP_MARKER_DISPLAY_MAX_AGE_MS } from '@/lib/constants';

export type MarkerBehaviorKind =
  | 'drift'
  | 'fast'
  | 'strike'
  | 'float'
  | 'watch'
  | 'static';

export type MarkerBehavior = {
  kind: MarkerBehaviorKind;
  cssClass: string;
  opacity: number;
  haloOpacity: number;
  haloRadiusPx: number;
  sizeScale: number;
  pulseMs: number;
};

const STATIC_TYPES = new Set([
  'explosion',
  'vibuh',
  'alert',
  'allclear',
  'chemical',
  'nuclear',
  'artillery',
  'obstril',
  'info',
]);

/** Epoch ms for «how fresh is this pin» — observation → update → created → parsed date. */
export function markerTimestampMs(marker: Marker): number {
  const lastObs = Number(marker.last_observation_epoch);
  if (Number.isFinite(lastObs) && lastObs > 0) return lastObs > 10_000_000_000 ? lastObs : lastObs * 1000;
  const last = Number(marker.last_update_epoch);
  if (Number.isFinite(last) && last > 0) return last > 10_000_000_000 ? last : last * 1000;
  const created = Number(marker.created_at_epoch);
  if (Number.isFinite(created) && created > 0) return created > 10_000_000_000 ? created : created * 1000;
  if (marker.date) {
    const parsed = new Date(marker.date).getTime();
    if (Number.isFinite(parsed) && parsed > 0) return parsed;
  }
  return Date.now();
}

export function markerPassesMapDisplayAge(marker: Marker, nowMs = Date.now()): boolean {
  return nowMs - markerTimestampMs(marker) <= MAP_MARKER_DISPLAY_MAX_AGE_MS;
}

export function filterMarkersForMapDisplay(markers: Marker[], nowMs = Date.now()): Marker[] {
  return markers.filter((m) => markerPassesMapDisplayAge(m, nowMs));
}

function clamp(v: number, min: number, max: number): number {
  if (!Number.isFinite(v)) return min;
  return Math.max(min, Math.min(max, v));
}

function typeBehavior(threatType: string): Pick<MarkerBehavior, 'kind' | 'pulseMs' | 'haloRadiusPx' | 'haloOpacity' | 'sizeScale'> {
  if (STATIC_TYPES.has(threatType)) {
    return { kind: 'static', pulseMs: 0, haloRadiusPx: 0, haloOpacity: 0, sizeScale: 1 };
  }
  if (threatType === 'ballistic') {
    return { kind: 'strike', pulseMs: 0, haloRadiusPx: 0, haloOpacity: 0, sizeScale: 1.08 };
  }
  if (threatType === 'missile' || threatType === 'raketa' || threatType === 'krylata' || threatType === 'pusk') {
    return { kind: 'fast', pulseMs: 0, haloRadiusPx: 0, haloOpacity: 0, sizeScale: 1.04 };
  }
  if (threatType === 'kab' || threatType === 'rszv') {
    return { kind: 'strike', pulseMs: 0, haloRadiusPx: 0, haloOpacity: 0, sizeScale: 1 };
  }
  if (threatType === 'air_balloon') {
    return { kind: 'float', pulseMs: 0, haloRadiusPx: 0, haloOpacity: 0, sizeScale: 0.94 };
  }
  if (threatType === 'rozved' || threatType === 'recon') {
    return { kind: 'watch', pulseMs: 0, haloRadiusPx: 0, haloOpacity: 0, sizeScale: 0.96 };
  }
  return { kind: 'drift', pulseMs: 0, haloRadiusPx: 0, haloOpacity: 0, sizeScale: 1 };
}

/** Visual behavior for map icons — halo intensity scales with track_state confidence. */
export function markerBehavior(marker: Marker, _nowMs = Date.now()): MarkerBehavior {
  const threatType = String(marker.threat_type || marker.type || 'shahed').toLowerCase();
  const trackState = String(marker.track_state || 'observed');

  // ── Loitering override: circular animation, no directional arrow ──────────
  if (marker.is_loitering) {
    const loiterScale = trackState === 'stale' ? 0.4 : trackState === 'lost' ? 0 : 0.7;
    return {
      kind: 'float',
      cssClass: 'behavior-float behavior-loitering',
      opacity: trackState === 'stale' ? 0.55 : trackState === 'lost' ? 0.25 : 0.88,
      haloOpacity: 0.18 * loiterScale,
      haloRadiusPx: 20 * (loiterScale > 0 ? 1 : 0),
      sizeScale: 0.95,
      pulseMs: 2200,
    };
  }

  const base = typeBehavior(threatType);

  // ── Halo scales with track_state ─────────────────────────────────────────
  let haloScale = 0;
  if (trackState === 'extrapolated') haloScale = 0.6;

  // ── Opacity: track_state base ─────────────────────────────────────────────
  let opacity = 1.0;
  if (trackState === 'lost') opacity = 0.25;
  else if (trackState === 'extrapolated') opacity = 0.8;

  // ── display_confidence further reduces opacity for uncertain positions ────
  // display_confidence <50 = area_circle; 50-69 = dashed; 70-89 = semi; ≥90 = full
  const dc = marker.display_confidence;
  if (dc != null) {
    if (dc < 50) opacity *= 0.6;
    else if (dc < 70) opacity *= 0.8;
  }

  // ── heading_confidence='unknown' dims marker slightly ─────────────────────
  if (marker.heading_confidence === 'unknown' && trackState === 'observed') {
    opacity = Math.min(opacity, 0.72);
    haloScale *= 0.5;
  } else if (marker.heading_confidence === 'regional') {
    opacity = Math.min(opacity, 0.88);
  }

  return {
    ...base,
    cssClass: `behavior-${base.kind}`,
    opacity,
    haloOpacity: base.haloOpacity * haloScale,
    haloRadiusPx: base.haloRadiusPx * (haloScale > 0 ? 1 : 0),
    sizeScale: clamp(base.sizeScale * (trackState === 'extrapolated' ? 0.96 : 1), 0.85, 1.12),
  };
}
