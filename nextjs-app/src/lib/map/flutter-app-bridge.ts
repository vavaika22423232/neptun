/**
 * Flutter WebView инжектит JavaScript-channel `NeptunApp`; сообщения — строка JSON.
 * @see neptun_alarm_app MapTab `_initWebView`
 */
import type { Marker, Trajectory, TrackPosition } from '@/types';

export type FlutterThreatMarkerTapEnvelope = {
  type: 'threat_marker_tap';
  marker: Record<string, unknown>;
};

declare global {
  interface Window {
    NeptunApp?: { postMessage: (message: string) => void };
  }
}

function addStr(dst: Record<string, unknown>, k: string, v: string | undefined | null) {
  if (v != null && String(v).trim().length > 0) dst[k] = v;
}

function addNum(dst: Record<string, unknown>, k: string, v: number | null | undefined) {
  if (v != null && Number.isFinite(v)) dst[k] = v;
}

function trajectoryForFlutter(t: Trajectory): Record<string, unknown> {
  const ti = t as Trajectory & { source_name?: string; target_name?: string };
  const o: Record<string, unknown> = {
    predicted: t.predicted ?? false,
  };
  if (t.start) o.start = t.start;
  if (t.end) o.end = t.end;
  if (t.prediction_confidence != null) o.prediction_confidence = t.prediction_confidence;
  addStr(o, 'source_name', ti.source_name ?? (typeof t.source === 'string' ? t.source : undefined));
  addStr(o, 'target_name', ti.target_name);
  addStr(o, 'source', t.source);
  if (t.waypoints?.length) o.waypoints = t.waypoints;
  addStr(o, 'flight_phase', t.flight_phase);
  return o;
}

function positionsForFlutter(rows: TrackPosition[]): unknown[] {
  return rows.map((p) => ({ lat: p.lat, lng: p.lng, ts: p.ts }));
}

/** Поля совместимы с `ThreatMarker.fromJson` (Dart) плюс сырые `track_state`, `last_update_epoch`. */
export function buildFlutterThreatMarkerPayload(m: Marker): Record<string, unknown> {
  const payload: Record<string, unknown> = {
    lat: m.lat,
    lng: m.lng,
    threat_type: m.threat_type || m.type || 'default',
  };
  addStr(payload, 'id', m.id);
  addStr(payload, 'track_id', m.track_id);
  addStr(payload, 'place', m.place || m.region || m.oblast);
  addStr(payload, 'text', m.text);
  addStr(payload, 'date', m.date);
  if (m.count != null) payload.count = m.count;
  addStr(payload, 'marker_icon', m.marker_icon);
  addNum(payload, 'course_bearing', m.course_bearing ?? undefined);
  addNum(payload, 'ticker_bearing', m.ticker_bearing ?? undefined);
  addStr(payload, 'course_direction', m.course_direction);
  addStr(payload, 'arrow_direction', m.arrow_direction);
  addNum(payload, 'distance_km', m.distance_km);
  addNum(payload, 'confidence_0_100', m.confidence_0_100);
  addStr(payload, 'placement_mode', m.placement_mode);
  addNum(payload, 'confidence', m.prediction_confidence ?? m.confidence);

  addStr(payload, 'track_state', m.track_state);
  if (m.last_update_epoch != null) payload.last_update_epoch = m.last_update_epoch;
  addStr(payload, 'origin', m.origin);
  addStr(payload, 'resolve_status', m.resolve_status);
  addStr(payload, 'motion_reason', m.motion_reason);

  addStr(payload, 'display_trust_hint_uk', m.display_trust_hint_uk);

  if (m.trajectory) {
    payload.trajectory = trajectoryForFlutter(m.trajectory);
  }
  if (m.positions?.length) {
    payload.positions = positionsForFlutter(m.positions);
  }

  return payload;
}

export function notifyFlutterThreatMarkerTap(m: Marker): boolean {
  try {
    if (typeof window === 'undefined') return false;
    const ch = window.NeptunApp;
    if (!ch?.postMessage) return false;
    const envelope: FlutterThreatMarkerTapEnvelope = {
      type: 'threat_marker_tap',
      marker: buildFlutterThreatMarkerPayload(m),
    };
    ch.postMessage(JSON.stringify(envelope));
    return true;
  } catch {
    return false;
  }
}
