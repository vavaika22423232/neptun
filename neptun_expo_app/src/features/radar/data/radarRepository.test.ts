import {
  countActiveRegionsFromAlarmStream,
  normalizeThreatMarker,
  parseThreatsEnvelope,
} from './radarParsing';

function assert(cond: boolean, msg: string): void {
  if (!cond) throw new Error(msg);
}

// Flutter `radar_repository_test.dart` parity
assert(parseThreatsEnvelope([{ id: 'a', threatType: 'shahed' }]).length === 1, 'array envelope');
assert(
  parseThreatsEnvelope({ threats: [{ id: '1', type: 'raketa' }] }).length === 1,
  'threats key',
);
assert(parseThreatsEnvelope({ markers: [] }).length === 0, 'empty markers');
assert(parseThreatsEnvelope('x').length === 0, 'unsupported');

const norm = normalizeThreatMarker({
  id: 't1',
  trackQualityScore: 0.82,
  formationId: 'wave-7',
  maneuverDetected: true,
  predictedImpact: { eta_minutes: 12 },
});
assert(norm.track_quality_score === 0.82, 'quality');
assert(norm.formation_id === 'wave-7', 'formation');
assert(norm.maneuver_detected === true, 'maneuver');
assert(typeof norm.predicted_impact === 'object', 'impact');

assert(
  countActiveRegionsFromAlarmStream([
    { activeAlerts: ['a'] },
    { activeAlerts: [] },
    { region: 'x' },
  ]) === 1,
  'alarm count',
);

console.log('radarRepository.test.ts: ok');
