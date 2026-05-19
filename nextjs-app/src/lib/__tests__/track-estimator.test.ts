import assert from 'node:assert/strict';

import { TRACK_MOTION_PROFILES } from '../track-motion-profile';
import {
  decideRealisticTickerStep,
  decideTrackObservationUpdate,
  estimateTrackState,
  trackMotionProfile,
} from '../track-estimator';
import { markerBehavior } from '../marker-behavior';

function test(name: string, fn: () => void): void {
  try {
    fn();
    console.log(`ok - ${name}`);
  } catch (error) {
    console.error(`not ok - ${name}`);
    throw error;
  }
}

const now = Date.now();

test('large jump versus shahed motion budget yields split_candidate observation decision', () => {
  const existing = {
    lat: 49,
    lng: 32,
    threat_type: 'shahed',
    confidence: 0.9,
    speed_kmh: 170,
    created_at_epoch: now - 120_000,
    observations: [{ lat: 49, lng: 32, ts: now - 120_000, source: 'a' }],
  };
  const incoming = {
    lat: 49.8,
    lng: 32,
    threat_type: 'shahed',
    confidence: 0.88,
    created_at_epoch: now,
  };
  const d = decideTrackObservationUpdate({ existing, incoming, nowMs: now });
  assert.equal(d.action, 'split_candidate');
  assert.equal(d.reason, 'teleport_blocked_split_candidate');
});

test('shahed remains extrapolated longer than missile with decayed confidence', () => {
  const estimate = estimateTrackState({
    lat: 49,
    lng: 32,
    threat_type: 'shahed',
    speed_kmh: 180,
    ticker_bearing: 90,
    confidence: 0.9,
    observations: [{ lat: 49, lng: 32, ts: now - 8 * 60_000 }],
  }, now);

  assert.equal(estimate.state, 'extrapolated');
  assert.equal(estimate.isEstimated, true);
  assert.ok(estimate.lng > 32);
  assert.ok(estimate.visualConfidence < 0.9);
});

test('missile enters terrain_masking quickly when observation is old', () => {
  const estimate = estimateTrackState({
    lat: 49,
    lng: 32,
    threat_type: 'missile',
    speed_kmh: 900,
    ticker_bearing: 90,
    confidence: 0.9,
    observations: [{ lat: 49, lng: 32, ts: now - 6 * 60_000 }],
  }, now);

  assert.equal(estimate.state, 'terrain_masking');
  assert.equal(estimate.isEstimated, true);
});

test('ballistic track is lost after short TTL', () => {
  const estimate = estimateTrackState({
    lat: 49,
    lng: 32,
    threat_type: 'ballistic',
    speed_kmh: 3000,
    ticker_bearing: 45,
    confidence: 0.95,
    observations: [{ lat: 49, lng: 32, ts: now - 6 * 60_000 }],
  }, now);

  assert.equal(estimate.state, 'lost');
  assert.ok(estimate.visualConfidence < 0.1);
});

test('air balloon drifts slowly and keeps a long extrapolation window', () => {
  const profile = trackMotionProfile('air_balloon');
  const estimate = estimateTrackState({
    lat: 49,
    lng: 32,
    threat_type: 'air_balloon',
    speed_kmh: 45,
    ticker_bearing: 180,
    confidence: 0.7,
    observations: [{ lat: 49, lng: 32, ts: now - 30 * 60_000 }],
  }, now);

  assert.ok(profile.extrapolateMs >= 60 * 60_000);
  assert.equal(estimate.state, 'extrapolated');
  assert.ok(estimate.lat < 49);
});

test('KAB keeps a medium extrapolation window and then becomes stale', () => {
  const freshKab = estimateTrackState({
    lat: 49,
    lng: 32,
    threat_type: 'kab',
    speed_kmh: 650,
    ticker_bearing: 270,
    confidence: 0.8,
    observations: [{ lat: 49, lng: 32, ts: now - 4 * 60_000 }],
  }, now);
  assert.equal(freshKab.state, 'extrapolated');
  assert.ok(freshKab.lng < 32);

  const staleKab = estimateTrackState({
    lat: 49,
    lng: 32,
    threat_type: 'kab',
    speed_kmh: 650,
    ticker_bearing: 270,
    confidence: 0.8,
    observations: [{ lat: 49, lng: 32, ts: now - 12 * 60_000 }],
  }, now);
  assert.equal(staleKab.state, 'stale');
});

test('realistic ticker refuses to move stale missile but moves fresh shahed', () => {
  const staleMissile = decideRealisticTickerStep({
    nowMs: now,
    tickIntervalMs: 15_000,
    marker: {
      lat: 49,
      lng: 32,
      threat_type: 'missile',
      speed_kmh: 900,
      ticker_bearing: 90,
      observations: [{ lat: 49, lng: 32, ts: now - 11 * 60_000 }],
    },
  });
  assert.equal(staleMissile.shouldTick, false);
  assert.equal(staleMissile.reason, 'lost');

  const freshShahed = decideRealisticTickerStep({
    nowMs: now,
    tickIntervalMs: 15_000,
    marker: {
      lat: 49,
      lng: 32,
      threat_type: 'shahed',
      speed_kmh: 180,
      ticker_bearing: 90,
      observations: [{ lat: 49, lng: 32, ts: now - 30_000 }],
    },
  });
  assert.equal(freshShahed.shouldTick, true);
  assert.ok(freshShahed.shouldTick && freshShahed.nextLng > 32);
});

test('realistic ticker stops near target and never advances lost ballistic', () => {
  const nearTarget = decideRealisticTickerStep({
    nowMs: now,
    tickIntervalMs: 15_000,
    marker: {
      lat: 49,
      lng: 32,
      threat_type: 'shahed',
      speed_kmh: 170,
      ticker_bearing: 90,
      trajectory: { end: [49.001, 32.001] },
      observations: [{ lat: 49, lng: 32, ts: now - 30_000 }],
    },
  });
  assert.equal(nearTarget.shouldTick, false);
  assert.equal(nearTarget.reason, 'near_target');

  const lostBallistic = decideRealisticTickerStep({
    nowMs: now,
    tickIntervalMs: 15_000,
    marker: {
      lat: 49,
      lng: 32,
      threat_type: 'ballistic',
      speed_kmh: 2500,
      ticker_bearing: 90,
      observations: [{ lat: 49, lng: 32, ts: now - 7 * 60_000 }],
    },
  });
  assert.equal(lostBallistic.shouldTick, false);
  assert.equal(lostBallistic.reason, 'lost');
});

test('observation lifecycle accepts plausible movement and blocks impossible jumps', () => {
  const existing = {
    lat: 49,
    lng: 32,
    threat_type: 'shahed',
    speed_kmh: 170,
    confidence: 0.8,
    observations: [{ lat: 49, lng: 32, ts: now - 60_000 }],
  };

  const accepted = decideTrackObservationUpdate({
    existing,
    incoming: { lat: 49.02, lng: 32.05, confidence: 0.82, created_at_epoch: now },
    nowMs: now,
  });
  assert.equal(accepted.action, 'accept_position');
  assert.equal(accepted.reason, 'accepted');

  const impossibleJump = decideTrackObservationUpdate({
    existing,
    incoming: { lat: 50.7, lng: 30.5, confidence: 0.7, created_at_epoch: now },
    nowMs: now,
  });
  assert.equal(impossibleJump.action, 'split_candidate');
  assert.equal(impossibleJump.reason, 'teleport_blocked_split_candidate');
});

test('observation lifecycle keeps stale replay and weak low-confidence geo out of position', () => {
  const existing = {
    lat: 49,
    lng: 32,
    threat_type: 'shahed',
    speed_kmh: 170,
    confidence: 0.8,
    observations: [{ lat: 49, lng: 32, ts: now }],
  };

  const staleReplay = decideTrackObservationUpdate({
    existing,
    incoming: { lat: 49.01, lng: 32.01, confidence: 0.9, created_at_epoch: now - 60_000 },
    nowMs: now,
  });
  assert.equal(staleReplay.action, 'observation_only');
  assert.equal(staleReplay.reason, 'stale_observation');

  const weakGeo = decideTrackObservationUpdate({
    existing,
    incoming: { lat: 49.05, lng: 32.02, confidence: 0.35, created_at_epoch: now + 1_000 },
    nowMs: now + 1_000,
  });
  assert.equal(weakGeo.action, 'hold_position');
  assert.equal(weakGeo.reason, 'weak_geo_hold');
});

test('worker and Next motion profile nominal speeds stay aligned', () => {
  const expectedTypicalSpeeds: Record<string, number> = {
    shahed: 170,
    drone: 170,
    uav: 170,
    fpv: 120,
    air_balloon: 40,
    rozved: 110,
    missile: 850,
    raketa: 850,
    krylata: 850,
    pusk: 850,
    ballistic: 2400,
    kab: 600,
    rszv: 650,
    avia: 750,
  };

  for (const [threatType, speed] of Object.entries(expectedTypicalSpeeds)) {
    assert.equal(TRACK_MOTION_PROFILES[threatType]?.nominalSpeedKmh, speed, threatType);
  }
});

test('marker behavior differs by threat family and confidence state', () => {
  const shahed = markerBehavior({
    lat: 49,
    lng: 32,
    threat_type: 'shahed',
    confidence: 0.9,
    observations: [{ lat: 49, lng: 32, ts: now }],
  }, now);
  assert.equal(shahed.kind, 'drift');
  assert.equal(shahed.opacity, 1);
  assert.equal(shahed.haloOpacity, 0);

  const ballistic = markerBehavior({
    lat: 49,
    lng: 32,
    threat_type: 'ballistic',
    confidence: 0.9,
    observations: [{ lat: 49, lng: 32, ts: now }],
  }, now);
  assert.equal(ballistic.kind, 'strike');
  assert.equal(ballistic.pulseMs, 0);

  const stale = markerBehavior({
    lat: 49,
    lng: 32,
    threat_type: 'shahed',
    track_state: 'stale',
    track_confidence: 0.25,
    observations: [{ lat: 49, lng: 32, ts: now - 30 * 60_000 }],
  }, now);
  assert.equal(stale.haloOpacity, 0);
  assert.equal(stale.opacity, 1);
});
