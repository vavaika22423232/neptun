import { aggregateHeatmapCountsByStateId } from './heatmapAggregate';

function assert(cond: boolean, msg: string): void {
  if (!cond) throw new Error(msg);
}

const byState = aggregateHeatmapCountsByStateId({
  'Харківська область': 2,
  'Харківський район': 1,
});
assert(byState['19'] === 3, 'kharkiv oblast + district');
console.log('heatmapAggregate.test.ts OK');
