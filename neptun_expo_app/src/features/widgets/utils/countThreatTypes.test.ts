import { countThreatTypesFromMarkers } from './countThreatTypes';

function assert(cond: boolean, msg: string): void {
  if (!cond) throw new Error(msg);
}

const markers = [
  { threat_type: 'shahed' },
  { type: 'missile' },
  { threatType: 'kab' },
  { threat_type: 'ballistic' },
];

const counts = countThreatTypesFromMarkers(markers);
assert(counts.drones === 1, 'drones');
assert(counts.missiles === 1, 'missiles');
assert(counts.kab === 1, 'kab');
assert(counts.ballistic === 1, 'ballistic');

console.log('countThreatTypes.test.ts OK');
