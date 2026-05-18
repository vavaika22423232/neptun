import assert from 'node:assert/strict';

import type { AdminSettings } from '../admin/data';
import { TargetTrackerEngine, type CandidateEvent } from '../target-tracker-engine';

function test(name: string, fn: () => void): void {
  try {
    fn();
    console.log(`ok - ${name}`);
  } catch (error) {
    console.error(`not ok - ${name}`);
    throw error;
  }
}

function settings(overrides: Partial<AdminSettings> = {}): AdminSettings {
  return {
    monitorPeriod: 30,
    ttlEnabled: true,
    minConfidence: 0.65,
    minConfidenceUav: 0.45,
    spatialCorrelatorEnabled: true,
    corroborationMinObservations: 2,
    corroborationWindowMinutes: 30,
    corroborationMaxRadiusKm: 45,
    corroborationMinDistinctSources: 2,
    dualSourceMapGate: false,
    regionUncertaintyKm: 38,
    corroboratedUncertaintyKm: 9,
    ...overrides,
  };
}

const now = Date.now();

function event(patch: Partial<CandidateEvent> = {}): CandidateEvent {
  return {
    event_id: 'msg-1',
    ts: now,
    lat: 49.0,
    lng: 32.0,
    threat_type: 'shahed',
    region: 'Черкаська область',
    place: 'Черкаси',
    source: 'channel-a',
    channel_priority: 1,
    confidence: 0.98,
    locality_confidence: 0.98,
    raw: {
      text: 'Шахед на Черкаси',
      resolve_status: 'ok',
      placement_mode: 'point',
    },
    ...patch,
  };
}

test('single generic candidate event creates tracking target, not confirmed public marker', () => {
  const engine = new TargetTrackerEngine(settings());
  const decision = engine.ingest(event({ channel_priority: 3, confidence: 0.8 }));
  assert.equal(decision.action, 'TARGET_CREATED');
  assert.ok(decision.target);
  assert.equal(decision.target?.lifecycle_state, 'TRACKING');
  assert.equal(engine.snapshot().length, 1);
});

test('single official high-confidence candidate can create confirmed tracked target', () => {
  const engine = new TargetTrackerEngine(settings());
  const decision = engine.ingest(event({ channel_priority: 1, confidence: 0.98, locality_confidence: 0.98 }));
  assert.equal(decision.action, 'TARGET_CREATED');
  assert.equal(decision.target?.lifecycle_state, 'CONFIRMED');
});

test('replay fingerprint is suppressed idempotently', () => {
  const engine = new TargetTrackerEngine(settings());
  const first = engine.ingest(event({ fingerprint: 'same-fp' }));
  const replay = engine.ingest(event({ fingerprint: 'same-fp' }));
  assert.equal(first.action, 'TARGET_CREATED');
  assert.equal(replay.action, 'REPLAY_SUPPRESSED');
  assert.equal(engine.snapshot()[0].history.length, 1);
});

test('nearby temporal event updates existing target', () => {
  const engine = new TargetTrackerEngine(settings());
  const first = engine.ingest(event({ fingerprint: 'a', source: 'channel-a', channel_priority: 1 }));
  const second = engine.ingest(event({
    event_id: 'msg-2',
    fingerprint: 'b',
    ts: now + 60_000,
    lat: 49.03,
    lng: 32.04,
    source: 'channel-b',
    channel_priority: 1,
  }));
  assert.equal(first.action, 'TARGET_CREATED');
  assert.equal(second.action, 'TARGET_UPDATED');
  assert.equal(engine.snapshot().length, 1);
  assert.equal(engine.snapshot()[0].source_count, 2);
  assert.equal(engine.snapshot()[0].lifecycle_state, 'CONFIRMED');
  assert.equal(engine.snapshot()[0].last_association?.reason, 'associated');
  assert.equal(engine.snapshot()[0].last_association?.accepted, true);
  assert.equal(typeof engine.snapshot()[0].last_association?.score, 'number');
  assert.equal(engine.snapshot()[0].last_measurement?.source, 'channel-b');
  assert.equal(engine.snapshot()[0].last_observation?.source, 'channel-b');
  assert.equal(typeof engine.snapshot(now + 120_000)[0].predicted_position?.lat, 'number');
});

test('weak edge-of-radius event starts a separate target instead of a random merge', () => {
  const engine = new TargetTrackerEngine(settings());
  const first = engine.ingest(event({ fingerprint: 'edge-a', place: 'Черкаси' }));
  const second = engine.ingest(event({
    event_id: 'msg-2',
    fingerprint: 'edge-b',
    ts: now + 4 * 60_000,
    lat: 49.1,
    lng: 32.0,
    place: 'Сміла',
    source: 'channel-b',
  }));

  assert.equal(first.action, 'TARGET_CREATED');
  assert.equal(second.action, 'TARGET_CREATED');
  assert.equal(engine.snapshot().length, 2);
});

test('plausible noisy update is smoothed instead of teleporting to raw measurement', () => {
  const engine = new TargetTrackerEngine(settings());
  engine.ingest(event({ fingerprint: 'smooth-a', source: 'channel-a' }));
  const second = engine.ingest(event({
    event_id: 'msg-2',
    fingerprint: 'smooth-b',
    ts: now + 3 * 60_000,
    lat: 49.06,
    lng: 32.04,
    source: 'channel-b',
  }));
  const target = engine.snapshot()[0];

  assert.equal(second.action, 'TARGET_UPDATED');
  assert.ok(target.lat > 49.0);
  assert.ok(target.lat < 49.06);
  assert.ok(target.lng > 32.0);
  assert.ok(target.lng < 32.04);
  assert.ok((target.speed_estimate_kmh ?? 0) > 0);
});

test('sharp course reversal is not merged into an existing radar track', () => {
  const engine = new TargetTrackerEngine(settings());
  engine.ingest(event({
    fingerprint: 'turn-a',
    lat: 49.0,
    lng: 32.0,
    place: 'Старт',
    source: 'channel-a',
  }));
  const eastbound = engine.ingest(event({
    event_id: 'msg-2',
    fingerprint: 'turn-b',
    ts: now + 3 * 60_000,
    lat: 49.0,
    lng: 32.1,
    place: 'Схід',
    source: 'channel-b',
  }));
  const reversal = engine.ingest(event({
    event_id: 'msg-3',
    fingerprint: 'turn-c',
    ts: now + 6 * 60_000,
    lat: 49.0,
    lng: 32.04,
    place: 'Назад',
    source: 'channel-c',
  }));

  assert.equal(eastbound.action, 'TARGET_UPDATED');
  assert.equal(reversal.action, 'TARGET_CREATED');
  assert.equal(engine.snapshot().length, 2);
});

test('weak coarse update enriches history without moving a reliable target', () => {
  const engine = new TargetTrackerEngine(settings());
  engine.ingest(event({
    fingerprint: 'hold-a',
    lat: 49.0,
    lng: 32.0,
    place: 'Черкаси',
    confidence: 0.98,
    locality_confidence: 0.98,
  }));
  const before = engine.snapshot()[0];
  const weak = engine.ingest(event({
    event_id: 'msg-2',
    fingerprint: 'hold-b',
    ts: now + 5 * 60_000,
    lat: 49.04,
    lng: 32.05,
    place: 'Неточна точка',
    source: 'channel-b',
    confidence: 0.55,
    locality_confidence: 0.55,
    raw: {
      text: 'Шахед десь в районі Черкас',
      resolve_status: 'area_center',
      placement_mode: 'area',
    },
  }));
  const after = engine.snapshot()[0];

  assert.equal(weak.action, 'TARGET_UPDATED');
  assert.equal(engine.snapshot().length, 1);
  assert.equal(after.lat, before.lat);
  assert.equal(after.lng, before.lng);
  assert.equal(after.place, before.place);
  assert.equal(after.history.at(-1)?.reason, 'updated_position_held');
});

test('loitering wording marks target as orbiting instead of directional flight', () => {
  const engine = new TargetTrackerEngine(settings());
  const decision = engine.ingest(event({
    fingerprint: 'loiter-a',
    raw: {
      text: 'Шахед кружляє в районі Черкас',
      resolve_status: 'ok',
      placement_mode: 'point',
    },
  }));

  assert.equal(decision.action, 'TARGET_CREATED');
  const target = engine.snapshot()[0];
  assert.equal(target.is_loitering, true);
  assert.equal(target.heading_confidence, 'unknown');
  assert.equal(target.eta_seconds, null);
});

test('direction-only target mention gets estimated rendered position for radar display', () => {
  const engine = new TargetTrackerEngine(settings());
  const decision = engine.ingest(event({
    fingerprint: 'estimated-a',
    raw: {
      text: 'Шахед курсом на Черкаси',
      resolve_status: 'direction_geocode_fallback',
      placement_mode: 'target_only_no_current_position',
    },
  }));

  assert.equal(decision.action, 'TARGET_CREATED');
  const target = engine.snapshot()[0];
  assert.equal(target.position_estimated, true);
  assert.equal(target.heading_confidence, 'explicit');
  assert.equal(typeof target.rendered_lat, 'number');
  assert.equal(typeof target.rendered_lng, 'number');
});

test('extrapolated position keeps a moving target associated after a long reporting gap', () => {
  const engine = new TargetTrackerEngine(settings());
  engine.ingest(event({
    fingerprint: 'predict-a',
    lat: 49.0,
    lng: 32.0,
    place: 'Західна точка',
    source: 'channel-a',
  }));
  const moving = engine.ingest(event({
    event_id: 'msg-2',
    fingerprint: 'predict-b',
    ts: now + 3 * 60_000,
    lat: 49.0,
    lng: 32.1,
    place: 'Східна точка',
    source: 'channel-b',
  }));
  const later = engine.ingest(event({
    event_id: 'msg-3',
    fingerprint: 'predict-c',
    ts: now + 20 * 60_000,
    lat: 48.93,
    lng: 32.43,
    place: 'Продовження курсу',
    source: 'channel-c',
  }));

  assert.equal(moving.action, 'TARGET_UPDATED');
  assert.equal(later.action, 'TARGET_UPDATED');
  assert.equal(engine.snapshot().length, 1);
  assert.equal(engine.snapshot()[0].source_count, 3);
});

test('coasted track rejects side/backfill measurements outside its course corridor', () => {
  const engine = new TargetTrackerEngine(settings());
  engine.ingest(event({
    fingerprint: 'corridor-a',
    lat: 49.0,
    lng: 32.0,
    place: 'Західна точка',
    source: 'channel-a',
  }));
  const moving = engine.ingest(event({
    event_id: 'msg-2',
    fingerprint: 'corridor-b',
    ts: now + 3 * 60_000,
    lat: 49.0,
    lng: 32.1,
    place: 'Східна точка',
    source: 'channel-b',
  }));
  const backfill = engine.ingest(event({
    event_id: 'msg-3',
    fingerprint: 'corridor-c',
    ts: now + 13 * 60_000,
    lat: 49.02,
    lng: 32.07,
    place: 'Бокова точка',
    source: 'channel-c',
  }));

  assert.equal(moving.action, 'TARGET_UPDATED');
  assert.equal(backfill.action, 'TARGET_CREATED');
  assert.equal(engine.snapshot().length, 2);
});

test('group count and upstream track id are retained in target state', () => {
  const engine = new TargetTrackerEngine(settings());
  const first = engine.ingest(event({
    fingerprint: 'group-a',
    upstream_track_id: 'trk-group-1',
    count: 3,
  }));
  const second = engine.ingest(event({
    event_id: 'msg-2',
    fingerprint: 'group-b',
    upstream_track_id: 'trk-group-1',
    ts: now + 60_000,
    lat: 49.02,
    lng: 32.02,
    count: 2,
    source: 'channel-b',
  }));
  const target = engine.snapshot()[0];

  assert.equal(first.action, 'TARGET_CREATED');
  assert.equal(second.action, 'TARGET_UPDATED');
  assert.equal(engine.snapshot().length, 1);
  assert.equal(target.count, 3);
  assert.deepEqual(target.upstream_track_ids, ['trk-group-1']);
  assert.equal(target.history[0].count, 3);
});

test('same upstream track can continue across oblast boundary when motion is plausible', () => {
  const engine = new TargetTrackerEngine(settings());
  const first = engine.ingest(event({
    fingerprint: 'cross-a',
    upstream_track_id: 'trk-cross-1',
    lat: 49.0,
    lng: 32.0,
    region: 'Черкаська область',
    place: 'Черкаси',
  }));
  const second = engine.ingest(event({
    event_id: 'msg-2',
    fingerprint: 'cross-b',
    upstream_track_id: 'trk-cross-1',
    ts: now + 10 * 60_000,
    lat: 49.16,
    lng: 32.18,
    region: 'Кіровоградська область',
    place: 'Олександрівка',
    source: 'channel-b',
  }));

  assert.equal(first.action, 'TARGET_CREATED');
  assert.equal(second.action, 'TARGET_UPDATED');
  assert.equal(engine.snapshot().length, 1);
  assert.equal(engine.snapshot()[0].region, 'Кіровоградська область');
});

test('nearby explicit multi-target groups with different upstream ids do not merge', () => {
  const engine = new TargetTrackerEngine(settings());
  const first = engine.ingest(event({
    fingerprint: 'group-split-a',
    upstream_track_id: 'trk-group-a',
    count: 2,
  }));
  const second = engine.ingest(event({
    event_id: 'msg-2',
    fingerprint: 'group-split-b',
    upstream_track_id: 'trk-group-b',
    ts: now + 45_000,
    lat: 49.01,
    lng: 32.01,
    count: 3,
    source: 'channel-b',
  }));

  assert.equal(first.action, 'TARGET_CREATED');
  assert.equal(second.action, 'TARGET_CREATED');
  assert.equal(engine.snapshot().length, 2);
  assert.deepEqual(engine.snapshot().map((t) => t.count).sort((a, b) => a - b), [2, 3]);
});

test('corroborated multi-source target is promoted to verified public', () => {
  const engine = new TargetTrackerEngine(settings());
  engine.ingest(event({
    fingerprint: 'cor-a',
    source: 'channel-a',
    channel_priority: 3,
    confidence: 0.85,
    locality_confidence: 0.95,
  }));
  const second = engine.ingest(event({
    event_id: 'msg-2',
    fingerprint: 'cor-b',
    ts: now + 120_000,
    lat: 49.01,
    lng: 32.01,
    source: 'channel-b',
    channel_priority: 3,
    confidence: 0.85,
    locality_confidence: 0.95,
  }));
  assert.equal(second.action, 'TARGET_UPDATED');
  const target = engine.snapshot()[0];
  assert.equal(target.source_count, 2);
  assert.equal(target.lifecycle_state, 'CONFIRMED');
  assert.ok(target.confidence >= 0.95);
});

test('impossible jump is quarantined and does not move target', () => {
  const engine = new TargetTrackerEngine(settings());
  engine.ingest(event({ fingerprint: 'a' }));
  const before = engine.snapshot()[0];
  const jump = engine.ingest(event({
    event_id: 'msg-2',
    fingerprint: 'b',
    ts: now + 60_000,
    lat: 49.1,
    lng: 32.1,
    source: 'channel-b',
  }));
  const after = engine.snapshot()[0];
  assert.equal(jump.action, 'EVENT_QUARANTINED');
  assert.equal(engine.snapshot().length, 1);
  assert.equal(after.lat, before.lat);
  assert.equal(after.lng, before.lng);
});

test('ambiguous geocode candidate is rejected before target promotion', () => {
  const engine = new TargetTrackerEngine(settings());
  const decision = engine.ingest(event({
    fingerprint: 'ambiguous',
    raw: {
      text: 'Шахед на Черкаси',
      geocode_tier: 'multi',
      candidates_count: 3,
      resolve_status: 'ok',
      placement_mode: 'point',
    },
  }));
  assert.equal(decision.action, 'EVENT_QUARANTINED');
  assert.equal(engine.snapshot().length, 0);
});

test('property invariant: low locality confidence never confirms target', () => {
  for (let i = 0; i < 100; i++) {
    const engine = new TargetTrackerEngine(settings());
    const decision = engine.ingest(event({
      fingerprint: `low-${i}`,
      lat: 48 + (i % 10) * 0.01,
      lng: 31 + (i % 10) * 0.01,
      locality_confidence: (i % 40) / 100,
    }));
    assert.notEqual(decision.target?.lifecycle_state, 'CONFIRMED');
  }
});

test('chaos realtime invariant: destroyed target is not updated by later replay-like event', () => {
  const engine = new TargetTrackerEngine(settings());
  const created = engine.ingest(event({ fingerprint: 'a' }));
  assert.ok(created.target);
  engine.markLifecycle(created.target.id, 'DESTROYED', now + 120_000);
  const later = engine.ingest(event({
    fingerprint: 'b',
    event_id: 'msg-2',
    ts: now + 180_000,
    lat: 49.01,
    lng: 32.01,
  }));
  assert.equal(later.action, 'TARGET_CREATED');
  assert.equal(engine.snapshot().length, 2);
});

test('stale replay is quarantined and cannot move an existing target backwards', () => {
  const engine = new TargetTrackerEngine(settings());
  engine.ingest(event({ fingerprint: 'fresh-a', ts: now + 120_000, lat: 49.0, lng: 32.0 }));
  const replay = engine.ingest(event({
    fingerprint: 'old-b',
    event_id: 'old-msg',
    ts: now,
    lat: 49.04,
    lng: 32.04,
    source: 'channel-b',
  }));
  const target = engine.snapshot(now + 180_000)[0];

  assert.equal(replay.action, 'EVENT_QUARANTINED');
  assert.equal(replay.reason, 'stale_replay');
  assert.equal(target.lat, 49.0);
  assert.equal(target.lng, 32.0);
  assert.equal(target.history.at(-1)?.accepted, false);
});

test('targets age through stale and lost lifecycle without new ingest', () => {
  const engine = new TargetTrackerEngine(settings());
  const created = engine.ingest(event({ fingerprint: 'age-a', threat_type: 'ballistic' }));
  assert.equal(created.target?.lifecycle_state, 'CONFIRMED');

  const stale = engine.snapshot(now + 4 * 60_000)[0];
  const lost = engine.snapshot(now + 6 * 60_000)[0];

  assert.equal(stale.lifecycle_state, 'STALE');
  assert.equal(lost.lifecycle_state, 'LOST');
});
test('diverging targets from same group are tracked as a split swarm', () => {
  const engine = new TargetTrackerEngine(settings());
  // Parent group
  engine.ingest(event({
    fingerprint: 'parent-a',
    lat: 49.0,
    lng: 32.0,
    count: 10,
    source: 'channel-a'
  }));

  // Event that is spatially close but kinetically "impossible" or just new
  // Suppose 5 minutes later, it's 10km away.
  const split = engine.ingest(event({
    event_id: 'msg-split',
    fingerprint: 'split-b',
    ts: now + 5 * 60_000,
    lat: 49.1, // ~11km north
    lng: 32.0,
    count: 5,
    source: 'channel-b'
  }));

  assert.equal(split.action, 'TARGET_CREATED');
  assert.equal(split.reason, 'swarm_split');
  
  const targets = engine.snapshot();
  assert.equal(targets.length, 2);
  const child = targets.find(t => t.id === split.target?.id);
  const parent = targets.find(t => t.id !== split.target?.id);
  
  assert.equal(child?.parent_track_id, parent?.id);
  assert.equal(child?.history.some(h => h.reason === 'split_from_parent'), true);
});
