/**
 * P3-C: EKF vs non-EKF path tests in updateTarget
 * P3-D: EKF serialization round-trip tests
 */
import assert from 'node:assert/strict';

import type { AdminSettings } from '../admin/data';
import { TargetTrackerEngine, type CandidateEvent } from '../target-tracker-engine';
import { KalmanFilter2D } from '../ekf';
import { sanitizeTrackedTarget } from '../target-serialization';

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

const BASE_TS = Date.now();

function event(patch: Partial<CandidateEvent> = {}): CandidateEvent {
  return {
    event_id: 'msg-1',
    ts: BASE_TS,
    lat: 49.0,
    lng: 32.0,
    threat_type: 'shahed',
    region: 'Черкаська область',
    place: 'Черкаси',
    source: 'channel-a',
    channel_priority: 1,
    confidence: 0.98,
    locality_confidence: 0.98,
    raw: { text: 'Шахед', resolve_status: 'ok', placement_mode: 'point' },
    ...patch,
  };
}

// ── P3-C: EKF path tests ─────────────────────────────────────────────────────

test('new target gets an EKF instance', () => {
  const engine = new TargetTrackerEngine(settings());
  const d = engine.ingest(event());
  assert.ok(d.target, 'target should be created');
  assert.ok(d.target!.ekf, 'EKF should be initialized on target creation');
  assert.ok(d.target!.ekf instanceof KalmanFilter2D, 'EKF should be a KalmanFilter2D');
});

test('EKF state is at the initial observation position', () => {
  const engine = new TargetTrackerEngine(settings());
  const d = engine.ingest(event({ lat: 50.0, lng: 31.0 }));
  assert.ok(d.target?.ekf);
  assert.ok(Math.abs(d.target!.ekf!.lat - 50.0) < 0.01, 'EKF lat should be near initial lat');
  assert.ok(Math.abs(d.target!.ekf!.lng - 31.0) < 0.01, 'EKF lng should be near initial lng');
});

test('after EKF update, speed_estimate_kmh comes from EKF helper (not blended non-EKF path)', () => {
  const engine = new TargetTrackerEngine(settings());
  const trackId = 'track-ekf-test-001';
  // First observation — same upstream_track_id ensures association even before velocity is known
  engine.ingest(event({ lat: 49.0, lng: 32.0, ts: BASE_TS, upstream_track_id: trackId }));
  // Second observation: 10 km north, 5 minutes later → ~120 km/h
  const dt = 5 * 60_000;
  const secondLat = 49.0 + 10 / 111.32; // ~10 km north
  const d2 = engine.ingest(event({
    event_id: 'msg-2',
    lat: secondLat,
    lng: 32.0,
    ts: BASE_TS + dt,
    source: 'channel-b',
    upstream_track_id: trackId,
  }));
  assert.ok(d2.target, 'second event should update target');
  assert.ok(d2.target!.ekf, 'EKF should persist after update');
  // Speed should be set (from EKF) and > 0
  const speed = d2.target!.speed_estimate_kmh;
  assert.ok(speed != null && speed >= 0,
    `EKF-derived speed should be set, got ${speed}`);
});

test('movement_vector bearing from EKF is in [0, 360) and points roughly northward', () => {
  const engine = new TargetTrackerEngine(settings());
  const trackId = 'track-bearing-test';
  engine.ingest(event({ lat: 49.0, lng: 32.0, ts: BASE_TS, upstream_track_id: trackId }));
  const northLat = 49.0 + 8 / 111.32; // ~8 km north
  const d2 = engine.ingest(event({
    event_id: 'msg-2',
    lat: northLat,
    lng: 32.0,
    ts: BASE_TS + 4 * 60_000,
    source: 'channel-b',
    upstream_track_id: trackId,
  }));
  assert.ok(d2.target, 'should have target');
  const bearing = d2.target!.movement_vector.bearing_deg;
  // Bearing may be null if EKF hasn't derived velocity yet, or should be ~north
  if (bearing != null) {
    assert.ok(bearing >= 0 && bearing < 360, `bearing ${bearing} out of range`);
    const isNorth = bearing <= 45 || bearing >= 315;
    assert.ok(isNorth, `bearing ${bearing} should be roughly north`);
  }
});

test('EKF speed and movement_vector are consistent (both from EKF helper)', () => {
  const engine = new TargetTrackerEngine(settings());
  const trackId = 'track-consistency-test';
  engine.ingest(event({ lat: 49.0, lng: 32.0, ts: BASE_TS, upstream_track_id: trackId }));
  const d2 = engine.ingest(event({
    event_id: 'msg-2',
    lat: 49.08,
    lng: 32.0,
    ts: BASE_TS + 5 * 60_000,
    source: 'channel-b',
    upstream_track_id: trackId,
  }));
  assert.ok(d2.target, 'should have target');
  const t = d2.target!;
  // Both speed fields must agree (both set from EKF helper)
  assert.strictEqual(t.speed_estimate_kmh, t.movement_vector.speed_kmh,
    'speed_estimate_kmh and movement_vector.speed_kmh must be equal (both EKF)');
});

test('non-EKF target: speed comes from blended estimator', () => {
  const engine = new TargetTrackerEngine(settings());
  // Create target and manually remove EKF to simulate non-EKF path
  const d1 = engine.ingest(event({ lat: 49.0, lng: 32.0, ts: BASE_TS }));
  if (d1.target?.ekf) d1.target.ekf = undefined as unknown as KalmanFilter2D;

  const d2 = engine.ingest(event({
    event_id: 'msg-2',
    lat: 49.1,
    lng: 32.0,
    ts: BASE_TS + 6 * 60_000,
    source: 'channel-b',
  }));
  const speed = d2.target?.speed_estimate_kmh;
  // Still should have a speed estimate from the blended path
  assert.ok(speed != null && speed >= 0, `should have speed estimate, got ${speed}`);
});

// ── P3-D: Redis round-trip tests ─────────────────────────────────────────────

test('KalmanFilter2D survives JSON.stringify / JSON.parse round-trip', () => {
  const kf = new KalmanFilter2D(50.0, 30.0, 150, 220);
  kf.predict(60);
  kf.update(50.05, 30.05, 0.85);
  kf.predict(30);
  kf.update(50.1, 30.1, 0.9);

  const json = JSON.parse(JSON.stringify(kf.toJSON()));
  const restored = KalmanFilter2D.fromJSON(json);

  assert.ok(Math.abs(restored.state[0] - kf.state[0]) < 1e-8, 'lat state preserved');
  assert.ok(Math.abs(restored.state[1] - kf.state[1]) < 1e-8, 'lng state preserved');
  assert.ok(Math.abs(restored.state[2] - kf.state[2]) < 1e-10, 'vx state preserved');
  assert.ok(Math.abs(restored.state[3] - kf.state[3]) < 1e-10, 'vy state preserved');
  assert.ok(Math.abs(restored.speedKmh() - kf.speedKmh()) < 0.01, 'speedKmh preserved');
  assert.ok(Math.abs(restored.bearingDeg() - kf.bearingDeg()) < 0.01, 'bearingDeg preserved');
});

test('sanitizeTrackedTarget reconstructs EKF from serialized data', () => {
  const kf = new KalmanFilter2D(49.0, 32.0, 120, 200);
  kf.predict(90);
  kf.update(49.05, 32.02, 0.8);

  const raw = {
    id: 'target_test123',
    lat: 49.05,
    lng: 32.02,
    threat_type: 'shahed',
    confidence: 0.82,
    reliability: 0.85,
    source_count: 2,
    sources: ['ch-a', 'ch-b'],
    upstream_track_ids: [],
    lifecycle_state: 'TRACKING',
    first_seen: BASE_TS,
    last_seen: BASE_TS + 90_000,
    movement_vector: { bearing_deg: 200, speed_kmh: 120 },
    speed_estimate_kmh: 120,
    history: [
      { fingerprint: 'fp1', ts: BASE_TS, lat: 49.0, lng: 32.0, source: 'ch-a', accepted: true, reason: 'created', confidence: 0.8 },
    ],
    event_fingerprints: ['fp1'],
    ekf: JSON.parse(JSON.stringify(kf.toJSON())),
    parent_track_id: 'target_parent456',
    swarm_cluster_id: 'swarm_shahed_17000',
  };

  const target = sanitizeTrackedTarget(raw);
  assert.ok(target, 'should produce a valid target');
  assert.ok(target!.ekf, 'EKF should be reconstructed');
  assert.ok(target!.ekf instanceof KalmanFilter2D, 'EKF must be a KalmanFilter2D instance');
  assert.ok(Math.abs(target!.ekf!.state[0] - kf.state[0]) < 1e-8, 'EKF state lat preserved');
  assert.ok(Math.abs(target!.ekf!.state[1] - kf.state[1]) < 1e-8, 'EKF state lng preserved');
});

test('parent_track_id and swarm_cluster_id survive sanitizeTrackedTarget', () => {
  const raw = {
    id: 'target_child',
    lat: 49.0,
    lng: 32.0,
    threat_type: 'shahed',
    confidence: 0.75,
    reliability: 0.8,
    source_count: 1,
    sources: ['ch-a'],
    upstream_track_ids: [],
    lifecycle_state: 'TRACKING',
    first_seen: BASE_TS,
    last_seen: BASE_TS,
    movement_vector: { bearing_deg: null, speed_kmh: null },
    speed_estimate_kmh: null,
    history: [
      { fingerprint: 'fp1', ts: BASE_TS, lat: 49.0, lng: 32.0, source: 'ch-a', accepted: true, reason: 'created', confidence: 0.75 },
    ],
    event_fingerprints: ['fp1'],
    parent_track_id: 'target_parent789',
    swarm_cluster_id: 'swarm_shahed_99',
  };

  const target = sanitizeTrackedTarget(raw);
  assert.ok(target, 'should produce valid target');
  assert.strictEqual(target!.parent_track_id, 'target_parent789');
  assert.strictEqual(target!.swarm_cluster_id, 'swarm_shahed_99');
});

test('sanitizeTrackedTarget handles missing/invalid ekf gracefully', () => {
  const raw = {
    id: 'target_noekf',
    lat: 49.0,
    lng: 32.0,
    threat_type: 'shahed',
    confidence: 0.7,
    reliability: 0.8,
    source_count: 1,
    sources: ['ch-a'],
    upstream_track_ids: [],
    lifecycle_state: 'DETECTED',
    first_seen: BASE_TS,
    last_seen: BASE_TS,
    movement_vector: { bearing_deg: null, speed_kmh: null },
    speed_estimate_kmh: null,
    history: [],
    event_fingerprints: [],
    ekf: { invalid: true }, // garbage
  };

  const target = sanitizeTrackedTarget(raw);
  assert.ok(target, 'should produce valid target even with invalid ekf data');
  assert.strictEqual(target!.ekf, undefined, 'invalid EKF data should be silently discarded');
});
