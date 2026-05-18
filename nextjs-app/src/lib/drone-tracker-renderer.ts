/**
 * drone-tracker-renderer.ts
 *
 * Converts raw ingest TrackerEvent data into rich rendering descriptors.
 * Core problem: parsed `coords` = TARGET or last-known area, NOT current drone GPS.
 * All position/heading values are probabilistic estimates with explicit confidence tracking.
 */

import { haversineKm, destinationPoint } from '@/lib/marker-movement-policy';
import { trackMotionProfile } from '@/lib/track-motion-profile';

// ─── Types ───────────────────────────────────────────────────────────────────

export interface TrackerEvent {
  track_id: string;
  marker_id: string;
  /** geocoded coords of the MENTIONED location (target / patrol area / last known) */
  coords: [number, number]; // [lat, lon]
  place: string;
  region: string | null;
  speed_kmh: number;
  /** 0–100 */
  confidence: number;
  /** how coords were resolved */
  resolve:
    | 'ok'
    | 'direction_geocode_fallback'
    | 'area_center'
    | 'region_centroid'
    | 'approx'
    | 'failed';
  message_text: string;
  timestamp: string; // ISO8601
  /** Earlier events on the same track_id, oldest first */
  prev_events: TrackerEvent[];
  /** Threat type for kinematic profile selection (optional, defaults to 'shahed') */
  threat_type?: string;
}

export type HeadingSource = 'explicit' | 'track' | 'regional' | 'unknown';

export interface TrackerRenderDescriptor {
  /** Estimated CURRENT position (may be extrapolated from target coords + heading) */
  position: [number, number];
  /** True compass bearing 0–360, null if completely unknown */
  heading_deg: number | null;
  /** How we derived the heading */
  heading_confidence: HeadingSource;
  /** Drone is loitering / orbiting — no directional render */
  is_loitering: boolean;
  /** Position was back-projected from target, not directly observed */
  position_estimated: boolean;
  /** Geocoded target / destination, if known */
  target: [number, number] | null;
  /** Seconds until reaching target at given speed. null if not computable */
  eta_seconds: number | null;
  /**
   * 0–100 display confidence:
   * ≥90 → solid marker + solid arrow
   * 70–89 → solid marker + semi-transparent arrow
   * 50–69 → marker + dashed arrow / "?" indicator
   * <50  → area circle only, no directional arrow
   */
  display_confidence: number;
  /** Ordered oldest → newest, for fading polyline trail */
  trail: [number, number][];
}

// ─── Regional entry bearing corridors ────────────────────────────────────────

/**
 * Rule C: Shaheds enter Ukraine from predictable corridors based on border proximity.
 * These are nominal inbound bearings (direction the drone is flying, into Ukraine).
 */
const REGIONAL_ENTRY_BEARING: Record<string, number> = {
  // Northeast corridor (Russia/Belarus)
  'Сумська область': 215,
  'Харківська область': 220,
  'Чернігівська область': 195,
  'Луганська область': 240,
  // East corridor
  'Донецька область': 270,
  'Запорізька область': 290,
  // South corridor (Crimea / Black Sea)
  'Херсонська область': 320,
  'Миколаївська область': 310,
  'Одеська область': 45,  // often from the east / northeast over Black Sea
  'Кіровоградська область': 225,
  // Northwest (Belarus)
  'Київська область': 200,
  'Житомирська область': 185,
  'Рівненська область': 175,
  'Волинська область': 170,
};

const FALLBACK_ENTRY_BEARING = 220; // generic northeast/east if nothing matches

// ─── Geo utilities ────────────────────────────────────────────────────────────

function bearingBetween(
  fromLat: number, fromLon: number,
  toLat: number, toLon: number,
): number {
  const toRad = Math.PI / 180;
  const dLon = (toLon - fromLon) * toRad;
  const lat1 = fromLat * toRad;
  const lat2 = toLat * toRad;
  const y = Math.sin(dLon) * Math.cos(lat2);
  const x = Math.cos(lat1) * Math.sin(lat2) - Math.sin(lat1) * Math.cos(lat2) * Math.cos(dLon);
  const brg = (Math.atan2(y, x) / toRad + 360) % 360;
  return brg;
}

function tsMs(iso: string): number {
  const ms = new Date(iso).getTime();
  return Number.isFinite(ms) ? ms : Date.now();
}

// ─── Loitering detection ──────────────────────────────────────────────────────

const LOITER_PATTERNS = [
  /кружля/ui,
  /барражу/ui,
  /барражир/ui,
  /\bloiter/ui,
  /в\s+район[іи]/ui,
  /патрулю/ui,
  /кружить/ui,
];

/**
 * Rule E: detect loitering / orbit patterns in message text.
 * Loitering drones have no directional heading — render with circular animation.
 */
function detectLoitering(text: string): boolean {
  return LOITER_PATTERNS.some((re) => re.test(text));
}

// ─── Explicit direction extraction ───────────────────────────────────────────

const EXPLICIT_COURSE_PATTERNS = [
  /курсом\s+на\s+(.+?)(?:[,;.!)\n]|$)/ui,
  /рухається\s+(?:в\s+напрямку|на)\s+(.+?)(?:[,;.!)\n]|$)/ui,
  /летить\s+(?:в\s+напрямку\s+)?на\s+(.+?)(?:[,;.!)\n]|$)/ui,
  /➡️\s*на\s+(.+?)(?:[,;.!)\n]|$)/ui,
  /⬆️\s*на\s+(.+?)(?:[,;.!)\n]|$)/ui,
  /в\s+бік\s+(.+?)(?:[,;.!)\n]|$)/ui,
  /напрямок\s*[—:\-]\s*(.+?)(?:[,;.!)\n]|$)/ui,
];

/**
 * Rule A: Extract destination place name from message text.
 * Returns the raw place string for the caller to geocode.
 */
function extractExplicitDestinationName(text: string): string | null {
  for (const re of EXPLICIT_COURSE_PATTERNS) {
    const m = text.match(re);
    if (m?.[1]) {
      return m[1].trim().replace(/\s+/g, ' ').slice(0, 80);
    }
  }
  return null;
}

// ─── Regional fallback bearing ────────────────────────────────────────────────

/**
 * Rule C: Return the expected inbound bearing based on which Oblast the event is in.
 * Uses normalized NFKC comparison against canonical oblast names, with alias fallbacks.
 */
function normalizeOblast(s: string): string {
  return s.normalize('NFKC').trim().toLowerCase().replace(/\s+/g, ' ');
}

// Pre-normalized lookup built once at module load
const NORMALIZED_ENTRY_BEARING: Array<{ key: string; bearing: number }> =
  Object.entries(REGIONAL_ENTRY_BEARING).map(([key, bearing]) => ({
    key: normalizeOblast(key),
    bearing,
  }));

function regionalEntryBearing(region: string | null): number {
  if (!region) return FALLBACK_ENTRY_BEARING;
  const norm = normalizeOblast(region);
  // 1. Exact match
  for (const { key, bearing } of NORMALIZED_ENTRY_BEARING) {
    if (norm === key) return bearing;
  }
  // 2. Starts-with match (handles "Харківська" matching "Харківська область")
  for (const { key, bearing } of NORMALIZED_ENTRY_BEARING) {
    const firstWord = key.split(' ')[0]!;
    if (firstWord.length >= 5 && norm.startsWith(firstWord)) return bearing;
  }
  // 3. Contains match as last resort
  for (const { key, bearing } of NORMALIZED_ENTRY_BEARING) {
    const firstWord = key.split(' ')[0]!;
    if (firstWord.length >= 5 && norm.includes(firstWord)) return bearing;
  }
  return FALLBACK_ENTRY_BEARING;
}

// ─── Trail builder ────────────────────────────────────────────────────────────

/**
 * Collect positions from prev_events (oldest → newest) then append current event.
 * Only include positions that moved at least 1 km from the previous (dedup noise).
 */
function buildTrail(event: TrackerEvent): [number, number][] {
  const raw: [number, number][] = [
    ...event.prev_events.map((e) => e.coords as [number, number]),
    event.coords as [number, number],
  ];
  const out: [number, number][] = [];
  for (const pt of raw) {
    if (!Number.isFinite(pt[0]) || !Number.isFinite(pt[1])) continue;
    if (out.length === 0) { out.push(pt); continue; }
    const prev = out[out.length - 1]!;
    if (haversineKm(prev[0], prev[1], pt[0], pt[1]) >= 1.0) out.push(pt);
  }
  return out;
}

// ─── Position estimation from target ─────────────────────────────────────────

/**
 * Rule D: When we know the TARGET but not the origin/current position,
 * project BACKWARDS from target along the regional entry bearing by 50–150 km
 * to estimate where the drone approximately is now.
 *
 * Distance is scaled by how old the event is — older events = drone is closer.
 */
function estimatePositionFromTarget(
  target: [number, number],
  bearing: number,       // inbound bearing (toward target)
  event: TrackerEvent,
  nowMs: number,
): [number, number] {
  const profile = trackMotionProfile(event.threat_type ?? 'shahed');
  const ageMs = Math.max(0, nowMs - tsMs(event.timestamp));
  // Reverse bearing: drone approaches target from this direction
  const reverseBearing = (bearing + 180) % 360;
  // How far back to project: 120 km at t=0, shrinks as drone gets closer
  const progressFraction = Math.min(ageMs / (40 * 60_000), 1); // 40 min TTL
  const offsetKm = Math.max(5, 120 * (1 - progressFraction));
  const distTravelled = (profile.nominalSpeedKmh * ageMs) / 3_600_000;
  const finalOffset = Math.max(5, offsetKm - distTravelled);
  return destinationPoint(target[0], target[1], reverseBearing, finalOffset);
}

// ─── ETA calculation ──────────────────────────────────────────────────────────

/**
 * Estimate seconds until the drone reaches the target.
 * Applies a confidence penalty: uncertain headings inflate ETA.
 * Returns null if position or target is unavailable or speed too low.
 */
function computeEta(
  position: [number, number],
  target: [number, number] | null,
  speedKmh: number,
  headingSource: HeadingSource = 'unknown',
): number | null {
  if (!target || speedKmh < 10) return null; // <10 km/h = loitering/hover
  const distKm = haversineKm(position[0], position[1], target[0], target[1]);
  if (distKm < 0.5) return 0;
  const baseEtaSec = (distKm / speedKmh) * 3600;
  // Inflate ETA for uncertain headings to communicate unreliability
  const uncertainty = headingSource === 'explicit' ? 1.0
    : headingSource === 'track' ? 1.05
    : headingSource === 'regional' ? 1.3
    : null; // unknown → don't show ETA at all
  if (uncertainty == null) return null;
  return Math.round(baseEtaSec * uncertainty);
}

// ─── Confidence mapping ───────────────────────────────────────────────────────

/**
 * Map resolve type + raw confidence to display_confidence (0–100).
 *
 * - 'ok': trust the raw confidence value fully
 * - 'direction_geocode_fallback': heading unknown, apply Rule C penalty
 * - 'area_center': rough area only, reduce confidence significantly
 * - 'region_centroid': very rough, large area — further reduce
 * - 'approx': approximation — moderate penalty
 * - 'failed': no valid coords, minimum confidence
 */
function resolveDisplayConfidence(
  resolve: TrackerEvent['resolve'],
  rawConfidence: number,
  headingSource: HeadingSource,
): number {
  let base = Math.max(0, Math.min(100, rawConfidence));

  switch (resolve) {
    case 'ok':
      break; // use raw
    case 'direction_geocode_fallback':
      // Heading is unknown — we're applying Rule C regional fallback
      base = Math.min(base, 62);
      break;
    case 'approx':
      base = Math.min(base, 70);
      break;
    case 'area_center':
      base = Math.min(base, 52);
      break;
    case 'region_centroid':
      base = Math.min(base, 38);
      break;
    case 'failed':
      base = Math.min(base, 18);
      break;
  }

  // Degrade further if heading is unknown
  if (headingSource === 'unknown') base = Math.min(base, 45);
  if (headingSource === 'regional') base = Math.min(base, 65);

  return Math.round(base);
}

// ─── Main entry point ─────────────────────────────────────────────────────────

/**
 * Convert a raw TrackerEvent into a full rendering descriptor.
 *
 * Algorithm:
 * 1. Detect loitering (Rule E) — bail early if loitering.
 * 2. Try to derive heading from explicit text pattern (Rule A).
 * 3. Try to derive heading from sequential track events (Rule B) — most reliable.
 * 4. Fall back to regional corridor bearing (Rule C).
 * 5. Estimate current position: if we have a heading and target, project backwards.
 * 6. Compute trail from prev_events.
 * 7. Compute ETA.
 * 8. Map confidence to display_confidence.
 */
export function buildTrackerRenderDescriptor(
  event: TrackerEvent,
  nowMs = Date.now(),
): TrackerRenderDescriptor {
  const [targetLat, targetLon] = event.coords;
  const target: [number, number] = [targetLat, targetLon];
  const threatProfile = trackMotionProfile(event.threat_type ?? 'shahed');
  const speedKmh = event.speed_kmh > 0 ? event.speed_kmh : threatProfile.nominalSpeedKmh;

  // ── Rule E: Loitering detection ──────────────────────────────────────────
  if (detectLoitering(event.message_text)) {
    const trail = buildTrail(event);
    return {
      position: target,
      heading_deg: null,
      heading_confidence: 'unknown',
      is_loitering: true,
      position_estimated: false,
      target: null,
      eta_seconds: null,
      display_confidence: resolveDisplayConfidence(event.resolve, event.confidence, 'unknown'),
      trail,
    };
  }

  // ── Rule B: Sequential track events ─────────────────────────────────────
  // Most reliable: use prev→current displacement vector.
  let heading_deg: number | null = null;
  let headingSource: HeadingSource = 'unknown';
  let position: [number, number] = target; // default: put marker AT target
  let derivedTarget: [number, number] | null = target;

  if (event.prev_events.length > 0) {
    const prev = event.prev_events[event.prev_events.length - 1]!;
    const [pLat, pLon] = prev.coords;
    const distKm = haversineKm(pLat, pLon, targetLat, targetLon);
    if (distKm >= 2.0) {
      // Enough displacement to compute a reliable bearing
      heading_deg = bearingBetween(pLat, pLon, targetLat, targetLon);
      headingSource = 'track';
      // Current position: extrapolate from previous towards current
      const ageMs = Math.max(0, tsMs(event.timestamp) - tsMs(prev.timestamp));
      const travelledKm = (speedKmh * ageMs) / 3_600_000;
      if (travelledKm > 0 && travelledKm < distKm * 1.5) {
        // Place marker along the track at estimated current position
        position = destinationPoint(pLat, pLon, heading_deg, Math.min(travelledKm, distKm));
      } else {
        position = target; // fall back to target coords
      }
    }
  }

  // ── Rule A: Explicit direction in text ──────────────────────────────────
  // If text says "курсом на X", we know the destination but the coords IS the
  // mentioned place. The drone is approaching — so coords ≈ target, not origin.
  // We use regional bearing to project backwards for current position.
  if (heading_deg === null) {
    const destName = extractExplicitDestinationName(event.message_text);
    if (destName) {
      // We know the destination = event.coords (parser geocoded it as target).
      // Use regional bearing as the approach direction.
      const regionBearing = regionalEntryBearing(event.region);
      heading_deg = regionBearing;
      headingSource = 'explicit'; // text said "курсом на X" — explicit intent
      // Estimate where the drone is NOW: project backwards from target
      position = estimatePositionFromTarget(target, regionBearing, event, nowMs);
      derivedTarget = target;
    }
  }

  // ── Rule C: Regional corridor fallback ──────────────────────────────────
  // No explicit direction, no track. Use regional entry corridor bearing.
  if (heading_deg === null) {
    if (event.resolve === 'ok' || event.resolve === 'approx') {
      const regionBearing = regionalEntryBearing(event.region);
      heading_deg = regionBearing;
      headingSource = 'regional';
      // Project backwards: drone is approaching target from regional corridor
      position = estimatePositionFromTarget(target, regionBearing, event, nowMs);
      derivedTarget = target;
    } else if (
      event.resolve === 'direction_geocode_fallback' ||
      event.resolve === 'area_center' ||
      event.resolve === 'region_centroid'
    ) {
      // Rule C still applies but confidence is low — heading is best-guess only
      const regionBearing = regionalEntryBearing(event.region);
      heading_deg = regionBearing;
      headingSource = 'regional';
      position = target; // keep at target area, don't project (too uncertain)
      derivedTarget = null; // don't show ETA arrow
    }
    // resolve === 'failed': heading stays null, position stays at target coords
  }

  // Without a known heading, ETA and target arrow are meaningless
  if (heading_deg === null) derivedTarget = null;

  // ── Trail ────────────────────────────────────────────────────────────────
  const trail = buildTrail(event);

  // ── ETA ──────────────────────────────────────────────────────────────────
  const eta_seconds = computeEta(position, derivedTarget, speedKmh, headingSource);

  // ── Display confidence ───────────────────────────────────────────────────
  const display_confidence = resolveDisplayConfidence(event.resolve, event.confidence, headingSource);

  // True when we back-projected from target (Rule A, C/D) rather than directly observed
  const position_estimated =
    headingSource === 'explicit' ||
    (headingSource === 'regional' && (event.resolve === 'ok' || event.resolve === 'approx'));

  return {
    position,
    heading_deg,
    heading_confidence: headingSource,
    is_loitering: false,
    position_estimated,
    target: derivedTarget,
    eta_seconds,
    display_confidence,
    trail,
  };
}

// ─── Rendering hint helpers ───────────────────────────────────────────────────

export type ArrowStyle = 'solid' | 'semi' | 'dashed' | 'none';
export type MarkerShape = 'pin' | 'area_circle';

/**
 * Map display_confidence → visual rendering instructions.
 *
 * ≥90: full pin, solid arrow
 * 70–89: full pin, semi-transparent arrow
 * 50–69: full pin, dashed arrow with "?" overlay
 * <50: area circle only, no directional arrow
 */
export function renderingHintsFromConfidence(displayConfidence: number): {
  markerShape: MarkerShape;
  arrowStyle: ArrowStyle;
  markerOpacity: number;
} {
  if (displayConfidence >= 90) {
    return { markerShape: 'pin', arrowStyle: 'solid', markerOpacity: 1.0 };
  }
  if (displayConfidence >= 70) {
    return { markerShape: 'pin', arrowStyle: 'semi', markerOpacity: 0.9 };
  }
  if (displayConfidence >= 50) {
    return { markerShape: 'pin', arrowStyle: 'dashed', markerOpacity: 0.75 };
  }
  return { markerShape: 'area_circle', arrowStyle: 'none', markerOpacity: 0.55 };
}

/**
 * Format ETA for display.
 * Examples: "2хв", "14хв", "1год 3хв"
 */
export function formatEta(eta_seconds: number | null): string | null {
  if (eta_seconds == null || !Number.isFinite(eta_seconds) || eta_seconds < 0) return null;
  if (eta_seconds < 30) return '< 1хв';
  const totalMins = Math.round(eta_seconds / 60);
  if (totalMins < 60) return `${totalMins}хв`;
  const hours = Math.floor(totalMins / 60);
  const mins = totalMins % 60;
  return mins > 0 ? `${hours}год ${mins}хв` : `${hours}год`;
}
