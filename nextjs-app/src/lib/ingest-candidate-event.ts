import { computeMarkerEventFingerprint } from '@/lib/public-marker-policy';

type CandidateEventWire = {
  event_id?: string;
  fingerprint?: string;
  raw_text?: string;
  source?: string;
  channel_name?: string;
  channel_priority?: number;
  ts?: number | string;
  event_kind?: 'observation' | 'trajectory_update' | 'status_update';
  target_id?: string;
  threat_type: string;
  confidence?: number;
  bearing_deg?: number | null;
  locality?: {
    place?: string;
    region?: string;
    lat?: number;
    lng?: number;
    confidence?: number;
    resolve_status?: string;
    placement_mode?: string;
    geocode_tier?: string;
    candidates_count?: number;
  };
  geocoding_candidates?: Array<{
    lat: number;
    lng: number;
    confidence?: number;
    source?: string;
    place?: string;
    region?: string;
  }>;
};

function normalizeEpochMs(value: unknown): number {
  if (typeof value === 'number' && Number.isFinite(value) && value > 0) {
    return value > 10_000_000_000 ? Math.round(value) : Math.round(value * 1000);
  }
  if (typeof value === 'string' && value.trim()) {
    const t = new Date(value.includes('T') ? value : value.replace(' ', 'T')).getTime();
    if (Number.isFinite(t) && t > 0) return t;
  }
  return Date.now();
}

function chooseCoordinateEvidence(event: CandidateEventWire): {
  lat?: number;
  lng?: number;
  confidence?: number;
  source?: string;
  place?: string;
  region?: string;
  candidatesCount: number;
} {
  const candidates = Array.isArray(event.geocoding_candidates) ? event.geocoding_candidates : [];
  if (typeof event.locality?.lat === 'number' && typeof event.locality?.lng === 'number') {
    return {
      lat: event.locality.lat,
      lng: event.locality.lng,
      confidence: event.locality.confidence,
      place: event.locality.place,
      region: event.locality.region,
      candidatesCount: event.locality.candidates_count ?? candidates.length,
    };
  }
  if (candidates.length === 0) {
    return { candidatesCount: 0 };
  }
  const sorted = [...candidates].sort((a, b) => (b.confidence ?? 0) - (a.confidence ?? 0));
  return { ...sorted[0], candidatesCount: candidates.length };
}

export function candidateEventToEvidenceMarker(event: CandidateEventWire): {
  marker: Record<string, unknown> | null;
  rejected?: {
    code: 'NO_COORDINATE_EVIDENCE';
    event_fingerprint: string;
    reason: string;
  };
} {
  const coord = chooseCoordinateEvidence(event);
  const ts = normalizeEpochMs(event.ts);
  const marker: Record<string, unknown> = {
    id: event.event_id,
    msg_id: event.event_id,
    track_id: event.target_id,
    channel_name: event.channel_name || event.source,
    channel: event.source || event.channel_name,
    channel_priority: event.channel_priority,
    text: event.raw_text || '',
    threat_type: event.threat_type,
    type: event.threat_type,
    created_at_epoch: ts,
    date: new Date(ts).toISOString(),
    confidence: event.confidence,
    locality_confidence: event.locality?.confidence ?? coord.confidence,
    course_bearing: event.bearing_deg ?? undefined,
    place: event.locality?.place || coord.place || '',
    region: event.locality?.region || coord.region || '',
    resolve_status: event.locality?.resolve_status || (coord.candidatesCount > 1 ? 'ambiguous_no_point' : 'ok'),
    placement_mode: event.locality?.placement_mode || (coord.candidatesCount > 1 ? 'approximate' : 'point'),
    geocode_tier: event.locality?.geocode_tier || (coord.candidatesCount > 1 ? 'multi' : 'point'),
    candidates_count: event.locality?.candidates_count ?? coord.candidatesCount,
    candidates: event.geocoding_candidates,
    event_fingerprint: event.fingerprint,
    ingest_contract: 'candidate_event',
    event_kind: event.event_kind || 'observation',
  };

  if (typeof coord.lat !== 'number' || typeof coord.lng !== 'number') {
    const event_fingerprint = event.fingerprint || computeMarkerEventFingerprint(marker);
    return {
      marker: null,
      rejected: {
        code: 'NO_COORDINATE_EVIDENCE',
        event_fingerprint,
        reason: 'candidate_event has no geocoding candidate coordinates',
      },
    };
  }

  marker.lat = coord.lat;
  marker.lng = coord.lng;
  marker.event_fingerprint = event.fingerprint || computeMarkerEventFingerprint(marker);
  return { marker };
}
