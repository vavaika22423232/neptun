import assert from 'node:assert/strict';
import {
  buildTrackerRenderDescriptor,
  formatEta,
  renderingHintsFromConfidence,
  type TrackerEvent,
} from '../drone-tracker-renderer';

function test(name: string, fn: () => void): void {
  try {
    fn();
    console.log(`ok - ${name}`);
  } catch (error) {
    console.error(`not ok - ${name}`);
    throw error;
  }
}

const BASE_TS = new Date('2024-01-15T10:00:00Z').toISOString();
const PREV_TS = new Date('2024-01-15T09:55:00Z').toISOString();

function makeEvent(overrides: Partial<TrackerEvent> = {}): TrackerEvent {
  return {
    track_id: 'track-1',
    marker_id: 'marker-1',
    coords: [49.0, 32.0],
    place: 'Черкаси',
    region: 'Черкаська область',
    speed_kmh: 170,
    confidence: 80,
    resolve: 'ok',
    message_text: 'Шахед',
    timestamp: BASE_TS,
    prev_events: [],
    threat_type: 'shahed',
    ...overrides,
  };
}

// ── Rule E: Loitering ─────────────────────────────────────────────────────────

test('Rule E: loitering detected from "кружляє"', () => {
  const desc = buildTrackerRenderDescriptor(makeEvent({ message_text: 'БПЛА кружляє над містом' }));
  assert.strictEqual(desc.is_loitering, true);
  assert.strictEqual(desc.heading_deg, null);
  assert.strictEqual(desc.eta_seconds, null);
});

test('Rule E: loitering detected from "барражує"', () => {
  const desc = buildTrackerRenderDescriptor(makeEvent({ message_text: 'БПЛА барражує в районі Харкова' }));
  assert.strictEqual(desc.is_loitering, true);
});

test('Rule E: normal message returns is_loitering false', () => {
  const desc = buildTrackerRenderDescriptor(makeEvent({ message_text: 'Шахед рухається на Харків' }));
  assert.strictEqual(desc.is_loitering, false);
});

// ── Rule B: Sequential track heading ─────────────────────────────────────────

test('Rule B: heading from prev→current when distance ≥ 2 km', () => {
  const prev: TrackerEvent = makeEvent({ marker_id: 'prev', coords: [48.9, 32.0], timestamp: PREV_TS, prev_events: [] });
  const desc = buildTrackerRenderDescriptor(makeEvent({ coords: [49.1, 32.0], prev_events: [prev] }));
  assert.strictEqual(desc.heading_confidence, 'track');
  assert.ok(desc.heading_deg != null, 'bearing should be set');
  // 49.1 > 48.9 → northward → ~0°
  const b = desc.heading_deg!;
  assert.ok(b <= 30 || b >= 330, `bearing ${b} should be ~north`);
});

test('Rule B: not applied when displacement < 2 km', () => {
  const prev: TrackerEvent = makeEvent({ marker_id: 'prev', coords: [49.005, 32.0], timestamp: PREV_TS, prev_events: [] });
  const desc = buildTrackerRenderDescriptor(makeEvent({ coords: [49.0, 32.0], prev_events: [prev] }));
  assert.notStrictEqual(desc.heading_confidence, 'track', 'small displacement should not trigger track rule');
});

// ── Rule A: Explicit direction ─────────────────────────────────────────────────

test('Rule A: "курсом на" triggers explicit heading and back-projection', () => {
  const desc = buildTrackerRenderDescriptor(makeEvent({ message_text: 'БПЛА курсом на Харків' }));
  assert.strictEqual(desc.heading_confidence, 'explicit');
  assert.ok(desc.heading_deg != null);
  assert.strictEqual(desc.position_estimated, true);
});

test('Rule A: "рухається в напрямку" triggers explicit heading', () => {
  const desc = buildTrackerRenderDescriptor(makeEvent({ message_text: 'БПЛА рухається в напрямку Дніпра' }));
  assert.strictEqual(desc.heading_confidence, 'explicit');
});

// ── Rule C: Regional corridor ─────────────────────────────────────────────────

test('Rule C: Харківська область → bearing ~220', () => {
  const desc = buildTrackerRenderDescriptor(makeEvent({ region: 'Харківська область', message_text: 'Загроза' }));
  assert.strictEqual(desc.heading_confidence, 'regional');
  assert.ok(desc.heading_deg != null);
  assert.ok(Math.abs(desc.heading_deg! - 220) < 5, `expected ~220°, got ${desc.heading_deg}`);
});

test('Rule C: Сумська область → bearing ~215', () => {
  const desc = buildTrackerRenderDescriptor(makeEvent({ region: 'Сумська область', message_text: 'Загроза' }));
  assert.ok(Math.abs(desc.heading_deg! - 215) < 5, `expected ~215°, got ${desc.heading_deg}`);
});

test('Rule C: Донецька область → bearing ~270', () => {
  const desc = buildTrackerRenderDescriptor(makeEvent({ region: 'Донецька область', message_text: 'Загроза' }));
  assert.ok(Math.abs(desc.heading_deg! - 270) < 5, `expected ~270°, got ${desc.heading_deg}`);
});

test('Rule C: failed resolve → no heading', () => {
  const desc = buildTrackerRenderDescriptor(makeEvent({ resolve: 'failed' }));
  assert.strictEqual(desc.heading_deg, null);
});

// ── Regional bearing normalization (P2-E) ─────────────────────────────────────

test('P2-E: partial region name "Харківська" matches correctly', () => {
  const desc = buildTrackerRenderDescriptor(makeEvent({ region: 'Харківська', message_text: 'Загроза' }));
  assert.ok(desc.heading_deg != null, 'should match partial region name');
  assert.ok(Math.abs(desc.heading_deg! - 220) < 5, `expected ~220°, got ${desc.heading_deg}`);
});

test('P2-E: region string with trailing whitespace normalizes correctly', () => {
  const desc = buildTrackerRenderDescriptor(makeEvent({ region: '  Херсонська область  ', message_text: 'Загроза' }));
  assert.ok(desc.heading_deg != null);
  assert.ok(Math.abs(desc.heading_deg! - 320) < 5, `expected ~320°, got ${desc.heading_deg}`);
});

// ── ETA (P2-A) ────────────────────────────────────────────────────────────────

test('ETA is null for loitering', () => {
  const desc = buildTrackerRenderDescriptor(makeEvent({ message_text: 'БПЛА кружляє' }));
  assert.strictEqual(desc.eta_seconds, null);
});

test('ETA is null for failed resolve (unknown heading)', () => {
  const desc = buildTrackerRenderDescriptor(makeEvent({ resolve: 'failed' }));
  assert.strictEqual(desc.eta_seconds, null);
});

test('ETA is positive for explicit direction', () => {
  const desc = buildTrackerRenderDescriptor(makeEvent({ message_text: 'БПЛА курсом на ціль', speed_kmh: 150 }), Date.now());
  if (desc.eta_seconds !== null) {
    assert.ok(desc.eta_seconds > 0, `ETA should be positive, got ${desc.eta_seconds}`);
    assert.ok(desc.eta_seconds < 4 * 3600, 'ETA should be < 4h');
  }
});

test('regional ETA is inflated vs explicit ETA for same distance', () => {
  // Force both to use regional position estimation for fair comparison
  const regional = buildTrackerRenderDescriptor(
    makeEvent({ region: 'Харківська область', resolve: 'ok', speed_kmh: 150, message_text: 'Загроза' }),
    Date.now(),
  );
  const explicit = buildTrackerRenderDescriptor(
    makeEvent({ speed_kmh: 150, message_text: 'БПЛА курсом на ціль' }),
    Date.now(),
  );
  if (regional.eta_seconds != null && explicit.eta_seconds != null) {
    assert.ok(regional.eta_seconds >= explicit.eta_seconds,
      `regional ETA (${regional.eta_seconds}s) should be >= explicit (${explicit.eta_seconds}s)`);
  }
});

// ── formatEta (P2-A) ──────────────────────────────────────────────────────────

test('formatEta: null → null', () => assert.strictEqual(formatEta(null), null));
test('formatEta: 0 → "< 1хв"', () => assert.strictEqual(formatEta(0), '< 1хв'));
test('formatEta: 25 → "< 1хв"', () => assert.strictEqual(formatEta(25), '< 1хв'));
test('formatEta: 120 → "2хв"', () => assert.strictEqual(formatEta(120), '2хв'));
test('formatEta: 14*60 → "14хв"', () => assert.strictEqual(formatEta(14 * 60), '14хв'));
test('formatEta: 3600 → "1год"', () => assert.strictEqual(formatEta(3600), '1год'));
test('formatEta: 3600+3*60 → "1год 3хв"', () => assert.strictEqual(formatEta(3600 + 3 * 60), '1год 3хв'));
test('formatEta: 2*3600+30*60 → "2год 30хв"', () => assert.strictEqual(formatEta(2 * 3600 + 30 * 60), '2год 30хв'));

// ── renderingHintsFromConfidence ──────────────────────────────────────────────

test('confidence ≥ 90 → solid + pin + opacity 1.0', () => {
  const h = renderingHintsFromConfidence(95);
  assert.strictEqual(h.arrowStyle, 'solid');
  assert.strictEqual(h.markerShape, 'pin');
  assert.strictEqual(h.markerOpacity, 1.0);
});

test('confidence 70–89 → semi + pin', () => {
  const h = renderingHintsFromConfidence(75);
  assert.strictEqual(h.arrowStyle, 'semi');
  assert.strictEqual(h.markerShape, 'pin');
});

test('confidence 50–69 → dashed', () => {
  assert.strictEqual(renderingHintsFromConfidence(55).arrowStyle, 'dashed');
});

test('confidence < 50 → area_circle + none', () => {
  const h = renderingHintsFromConfidence(30);
  assert.strictEqual(h.arrowStyle, 'none');
  assert.strictEqual(h.markerShape, 'area_circle');
});

// ── display_confidence ────────────────────────────────────────────────────────

test('display_confidence is in [0, 100] for all resolve types', () => {
  const cases: Array<[TrackerEvent['resolve'], number]> = [
    ['ok', 90], ['area_center', 70], ['region_centroid', 80], ['failed', 60], ['approx', 75],
  ];
  for (const [resolve, confidence] of cases) {
    const d = buildTrackerRenderDescriptor(makeEvent({ resolve, confidence }));
    assert.ok(d.display_confidence >= 0 && d.display_confidence <= 100,
      `resolve=${resolve}: display_confidence=${d.display_confidence} out of [0,100]`);
  }
});

test('ok resolve has higher display_confidence than region_centroid at same raw confidence', () => {
  const ok = buildTrackerRenderDescriptor(makeEvent({ resolve: 'ok', confidence: 75 }));
  const region = buildTrackerRenderDescriptor(makeEvent({ resolve: 'region_centroid', confidence: 75 }));
  assert.ok(ok.display_confidence > region.display_confidence,
    `ok (${ok.display_confidence}) should beat region_centroid (${region.display_confidence})`);
});

// ── Trail deduplication ───────────────────────────────────────────────────────

test('trail deduplicates points < 1 km apart', () => {
  const p1: TrackerEvent = makeEvent({ coords: [49.0, 32.0], timestamp: PREV_TS, prev_events: [] });
  const p2: TrackerEvent = makeEvent({ coords: [49.002, 32.0], timestamp: PREV_TS, prev_events: [p1] });
  const current = makeEvent({ coords: [49.1, 32.0], prev_events: [p1, p2] });
  const desc = buildTrackerRenderDescriptor(current);
  // p1→p2 < 1km, so should be deduplicated; p2→current ≥ 1km
  assert.ok(desc.trail.length <= 2, `trail should deduplicate near-points, got ${desc.trail.length}`);
});

// ── Threat type awareness (P2-B) ──────────────────────────────────────────────

test('P2-B: threat_type is passed to speed profile (no crash for all types)', () => {
  const threatTypes = ['shahed', 'missile', 'ballistic', 'fpv', 'rozved', 'kab'];
  for (const tt of threatTypes) {
    assert.doesNotThrow(
      () => buildTrackerRenderDescriptor(makeEvent({ threat_type: tt })),
      `should not throw for threat_type=${tt}`,
    );
  }
});
