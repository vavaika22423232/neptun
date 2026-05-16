import assert from 'node:assert/strict';

import type { AdminSettings } from '../admin/data';
import {
  computeMarkerEventFingerprint,
  evaluateMarkerPublication,
} from '../public-marker-policy';
import { candidateEventToEvidenceMarker } from '../ingest-candidate-event';

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

const basePublicMarker = {
  id: 'm-1',
  lat: 49.0,
  lng: 32.0,
  threat_type: 'shahed',
  place: 'Черкаси',
  region: 'Черкаська область',
  text: 'Шахед на Черкаси',
  confidence: 0.98,
  resolve_status: 'ok',
  placement_mode: 'point',
  channel_name: 'trusted-a',
  channel_priority: 1,
  observations: [
    { lat: 49.0, lng: 32.0, ts: Date.now() - 60_000, source: 'trusted-a' },
    { lat: 49.01, lng: 32.01, ts: Date.now() - 30_000, source: 'trusted-b' },
  ],
};

test('verified marker is public only when all confidence dimensions pass', () => {
  const decision = evaluateMarkerPublication(basePublicMarker, { settings: settings() });
  assert.equal(decision.classification, 'VERIFIED_PUBLIC');
  assert.equal(decision.public, true);
  assert.ok(decision.score >= 0.95);
});

test('ambiguous geocode is admin-only or lower and never public', () => {
  const marker = {
    ...basePublicMarker,
    geocode_tier: 'multi',
    candidates_count: 2,
  };
  const decision = evaluateMarkerPublication(marker, { settings: settings() });
  assert.equal(decision.public, false);
  assert.ok(decision.invariantViolations.includes('unsafe_locality'));
  assert.ok(decision.score < 0.95);
});

test('fallback coordinates are never public even with high parser confidence', () => {
  const marker = {
    ...basePublicMarker,
    placement_mode: 'approximate',
    resolve_status: 'oblast_fallback',
    confidence: 1,
  };
  const decision = evaluateMarkerPublication(marker, { settings: settings() });
  assert.equal(decision.public, false);
  assert.ok(decision.invariantViolations.includes('unsafe_locality'));
});

test('synthetic phantom markers are never public', () => {
  const marker = {
    ...basePublicMarker,
    resolve_status: 'phantom_avia',
  };
  const decision = evaluateMarkerPublication(marker, { settings: settings() });
  assert.equal(decision.public, false);
  assert.ok(decision.invariantViolations.includes('synthetic_marker'));
});

test('event fingerprint is stable for replay protection', () => {
  const first = computeMarkerEventFingerprint({
    channel_name: 'ch',
    msg_id: 123,
    text: '  Шахед   на Черкаси ',
    threat_type: 'shahed',
    place: 'Черкаси',
    region: 'Черкаська область',
    created_at_epoch: 1710000000000,
  });
  const replay = computeMarkerEventFingerprint({
    region: 'Черкаська область',
    place: 'Черкаси',
    threat_type: 'shahed',
    text: 'Шахед на Черкаси',
    msg_id: 123,
    channel_name: 'ch',
    created_at_epoch: 1710000000000,
  });
  assert.equal(first, replay);
});

test('fuzz invariant: unsafe locality fields never produce public decisions', () => {
  const unsafe = [
    { geocode_tier: 'ambiguous' },
    { candidates_count: 4 },
    { placement_mode: 'approximate' },
    { resolve_status: 'oblast_fallback' },
    { place: 'воду' },
    { place: 'акваторія' },
    { track_state: 'split_candidate' },
  ];
  for (let i = 0; i < 120; i++) {
    const patch = unsafe[i % unsafe.length];
    const marker = {
      ...basePublicMarker,
      ...patch,
      lat: 46 + (i % 50) / 10,
      lng: 24 + (i % 120) / 10,
      confidence: 1,
    };
    const decision = evaluateMarkerPublication(marker, { settings: settings() });
    assert.equal(decision.public, false, `unsafe fuzz case ${i} became public`);
  }
});

test('chaos realtime invariant: REST and SSE policy decisions match', () => {
  const marker = { ...basePublicMarker };
  const restDecision = evaluateMarkerPublication(marker, { settings: settings() });
  const sseDecision = evaluateMarkerPublication({ ...marker }, { settings: settings() });
  assert.equal(restDecision.public, sseDecision.public);
  assert.equal(restDecision.classification, sseDecision.classification);
});

test('stateful invariant: tracked target must be confirmed before public rendering', () => {
  const marker = {
    ...basePublicMarker,
    target_lifecycle_state: 'TRACKING',
    target_confidence: 0.99,
    source_count: 2,
  };
  const decision = evaluateMarkerPublication(marker, { settings: settings() });
  assert.equal(decision.public, false);
  assert.ok(decision.invariantViolations.includes('target_not_confirmed'));
});

test('confirmed extrapolated tracked target can remain public during motion window', () => {
  const marker = {
    ...basePublicMarker,
    confidence: 0.52,
    target_confidence: 0.96,
    target_lifecycle_state: 'CONFIRMED',
    track_state: 'extrapolated',
    track_confidence: 0.52,
    source_count: 2,
    channel_priority: 3,
  };
  const decision = evaluateMarkerPublication(marker, { settings: settings() });
  assert.equal(decision.classification, 'VERIFIED_PUBLIC');
  assert.equal(decision.public, true);
  assert.ok(decision.reasons.includes('track_extrapolated'));
});

test('candidate-event contract: ambiguous candidates become non-public evidence, not direct markers', () => {
  const converted = candidateEventToEvidenceMarker({
    event_id: 'ce-1',
    raw_text: 'Шахед над водою',
    source: 'channel-a',
    channel_priority: 1,
    ts: Date.now(),
    threat_type: 'shahed',
    confidence: 0.99,
    locality: {
      place: 'воду',
      region: 'Одеська область',
    },
    geocoding_candidates: [
      { lat: 46.5, lng: 30.7, confidence: 0.8, place: 'Одеса', region: 'Одеська область' },
      { lat: 49.4, lng: 32.0, confidence: 0.78, place: 'Черкаси', region: 'Черкаська область' },
    ],
  });
  assert.ok(converted.marker);
  assert.equal(converted.marker?.ingest_contract, 'candidate_event');
  assert.equal(converted.marker?.geocode_tier, 'multi');
  const decision = evaluateMarkerPublication(converted.marker, { settings: settings() });
  assert.equal(decision.public, false);
  assert.ok(decision.invariantViolations.includes('unsafe_locality'));
});

test('candidate-event contract: unresolved events are quarantined before coordinates exist', () => {
  const converted = candidateEventToEvidenceMarker({
    event_id: 'ce-2',
    raw_text: 'Шахед курсом на область',
    source: 'channel-a',
    threat_type: 'shahed',
    confidence: 0.9,
  });
  assert.equal(converted.marker, null);
  assert.equal(converted.rejected?.code, 'NO_COORDINATE_EVIDENCE');
});

test('candidate-event contract: trajectory updates are not public point markers', () => {
  const converted = candidateEventToEvidenceMarker({
    event_id: 'ce-trajectory',
    event_kind: 'trajectory_update',
    target_id: 'target-existing',
    raw_text: 'Курсом на Черкаси',
    source: 'channel-a',
    channel_priority: 1,
    ts: Date.now(),
    threat_type: 'shahed',
    confidence: 0.9,
    bearing_deg: 35,
    locality: {
      place: 'Черкаси',
      region: 'Черкаська область',
      lat: 49,
      lng: 32,
      confidence: 0.7,
      resolve_status: 'direction_update_from_chain',
      placement_mode: 'predictive',
      geocode_tier: 'point',
    },
  });
  assert.ok(converted.marker);
  assert.equal(converted.marker?.track_id, 'target-existing');
  assert.equal(converted.marker?.event_kind, 'trajectory_update');
  const decision = evaluateMarkerPublication(converted.marker, { settings: settings() });
  assert.equal(decision.public, false);
});
