import assert from 'node:assert/strict';

import type { Alarm } from '@/types';
import { collectActiveAlarmSvgKeys, renderAlarmSvgDiff } from '../map/map-alarm-svg-renderer';

class FakeClassList {
  private values = new Set<string>();

  toggle(name: string, enabled: boolean): void {
    if (enabled) this.values.add(name);
    else this.values.delete(name);
  }

  contains(name: string): boolean {
    return this.values.has(name);
  }
}

class FakeNode {
  classList = new FakeClassList();
}

class FakeSvg {
  private nodes = new Map<string, FakeNode[]>();

  add(id: string): FakeNode {
    const node = new FakeNode();
    const existing = this.nodes.get(id) ?? [];
    existing.push(node);
    this.nodes.set(id, existing);
    return node;
  }

  querySelectorAll(selector: string): FakeNode[] {
    const match = selector.match(/^\[id="(.+)"\]$/);
    return match ? this.nodes.get(match[1]) ?? [] : [];
  }
}

function test(name: string, fn: () => void): void {
  try {
    fn();
    console.log(`ok - ${name}`);
  } catch (error) {
    console.error(`not ok - ${name}`);
    throw error;
  }
}

function activeAlarm(regionType: 'State' | 'District', regionId: string): Alarm {
  return {
    regionType,
    regionId,
    activeAlerts: [{ type: 'AIR', lastUpdate: '2026-04-28T00:00:00.000Z' }],
  };
}

test('collectActiveAlarmSvgKeys ignores inactive and malformed alarm rows', () => {
  const keys = collectActiveAlarmSvgKeys([
    activeAlarm('State', '12'),
    activeAlarm('District', '107'),
    { regionType: 'State', regionId: '99', activeAlerts: [] },
    { regionType: 'District', regionId: '', activeAlerts: [{ type: 'AIR' }] },
  ] as Alarm[]);

  assert.deepEqual([...keys].sort(), ['District:107', 'State:12']);
});

test('renderAlarmSvgDiff routes state and district alarms to separate SVG roots', () => {
  const states = new FakeSvg();
  const districts = new FakeSvg();
  const stateNode = states.add('12');
  const districtNode = districts.add('107');

  const first = renderAlarmSvgDiff(
    { statesSvg: states as unknown as SVGElement, districtsSvg: districts as unknown as SVGElement },
    [activeAlarm('State', '12'), activeAlarm('District', '107')],
    new Set(),
  );

  assert.equal(first.added, 2);
  assert.equal(first.removed, 0);
  assert.equal(first.missing.length, 0);
  assert.equal(stateNode.classList.contains('alarm'), true);
  assert.equal(districtNode.classList.contains('alarm'), true);

  const second = renderAlarmSvgDiff(
    { statesSvg: states as unknown as SVGElement, districtsSvg: districts as unknown as SVGElement },
    [activeAlarm('District', '107')],
    first.activeIds,
  );

  assert.equal(second.added, 0);
  assert.equal(second.removed, 1);
  assert.equal(stateNode.classList.contains('alarm'), false);
  assert.equal(districtNode.classList.contains('alarm'), true);
});

test('renderAlarmSvgDiff reports missing district ids instead of falling back to oblasts', () => {
  const states = new FakeSvg();
  states.add('12');

  const result = renderAlarmSvgDiff(
    { statesSvg: states as unknown as SVGElement, districtsSvg: null },
    [activeAlarm('District', '107')],
    new Set(),
  );

  assert.deepEqual(result.missing, ['District:107']);
  assert.equal(result.added, 0);
});
