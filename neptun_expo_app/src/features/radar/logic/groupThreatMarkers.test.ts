import { groupThreatMarkersByType, placesPreview } from './groupThreatMarkers';

function assert(cond: boolean, msg: string): void {
  if (!cond) throw new Error(msg);
}

const groups = groupThreatMarkersByType([
  { threatType: 'shahed', place: 'Київ' },
  { threatType: 'shahed', place: 'Одеса' },
  { type: 'raketa', place: 'Львів' },
]);
assert(groups.length === 2, 'two threat groups');
assert(groups.find((g) => g.type === 'shahed')?.markers.length === 2, 'shahed count');

assert(
  placesPreview([{ place: 'A' }, { place: 'B' }, { place: 'C' }]) === 'A, B',
  'places preview',
);

console.log('groupThreatMarkers.test.ts OK');
