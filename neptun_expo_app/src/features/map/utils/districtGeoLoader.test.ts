import { buildDistrictAlarmGeoJson, buildDistrictBorderGeoJson } from './districtGeoLoader';

function assert(cond: boolean, msg: string): void {
  if (!cond) throw new Error(msg);
}

const borders = buildDistrictBorderGeoJson();
assert(borders.features.length >= 100, 'district border features loaded');

const alarmed = buildDistrictAlarmGeoJson({
  stateAlarms: {},
  districtAlarms: { '107': true, '999999': true },
  stateThreatTypes: {},
  stateCount: 0,
  districtCount: 1,
  ballisticRegions: [],
});
assert(alarmed.features.length === 1, 'only known district ids render alarms');
assert(String(alarmed.features[0]?.properties?.regionId) === '107', 'regionId preserved');

console.log('districtGeoLoader.test.ts: ok');
