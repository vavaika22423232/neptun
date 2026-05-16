/**
 * Ingest: airborne / strike `threat_type` markers require active regional alarm at coords
 * (`/api/alarms/all`). Exemptions: `manual`, meta types (`alarm`, …), `default`, `air_balloon`, empty sea placements.
 *
 * Optional bypass list: env `INGEST_SKIP_AIR_ALARM_CHANNELS=user1,user2` (lower-case usernames).
 */

import fs from 'fs';
import path from 'path';
import type { Alarm } from '@/types';
import { loadAlarms } from '@/lib/alarms-data';
import {
  districtRegionNamesForAlarms,
  findOblastHascForRegionLabel,
  hascListForStateAlarms,
  normalizeAlarmRegionName,
  type OblastFeatureCollection,
} from '@/lib/map/alarm-hasc-filter';
import { findHascContainingPoint } from '@/lib/ukraine-oblast-validate';
import { findRayonNormalizedContainingPoint } from '@/lib/ukraine-raion-point';

/** Public `threat_type` values that require повітряна тривога coverage at coords. */
const GATED_THREAT_TYPES = new Set([
  // UAV / rozvidka
  'shahed',
  'drone',
  'uav',
  'fpv',
  'rozved',
  // Cruise / ballistic / launches
  'missile',
  'raketa',
  'ballistic',
  'launch',
  'pusk',
  // Guided bombs / MLRS
  'kab',
  'rszv',
  // Aviation
  'avia',
  'tu95',
  'tu_95',
  'strategic_bomber',
  // Strikes (often air-linked in channels)
  'explosion',
  'vibuh',
  'artillery',
  'obstril',
]);

/** Not gated — system/meta pins, balloon probes, unknown legacy bucket. */
const NEVER_AIR_ALARM_GATE = new Set(['alarm', 'alarm_cancel', 'default', 'info', 'air_balloon']);

function ingestChannelSkipsAirAlarmGate(marker: Record<string, unknown>): boolean {
  const ch = String(marker.channel_name || '').trim().toLowerCase();
  if (!ch) return false;
  const raw = process.env.INGEST_SKIP_AIR_ALARM_CHANNELS?.trim();
  if (!raw) return false;
  return raw.split(',').some((p) => p.trim().toLowerCase() === ch);
}

let oblastFcCache: OblastFeatureCollection | null = null;
let alarmsMemo: { atMs: number; list: Alarm[] | null } | null = null;
const ALARMS_MEMO_MS = 12_000;

function getOblastFeatureCollection(): OblastFeatureCollection {
  if (!oblastFcCache) {
    const file = path.join(process.cwd(), 'public', 'ukraine_oblasts.geojson');
    oblastFcCache = JSON.parse(fs.readFileSync(file, 'utf-8')) as OblastFeatureCollection;
  }
  return oblastFcCache;
}

async function alarmsSnapshot(): Promise<Alarm[] | null> {
  const now = Date.now();
  if (alarmsMemo && now - alarmsMemo.atMs < ALARMS_MEMO_MS) {
    return alarmsMemo.list;
  }
  const loaded = await loadAlarms();
  const list = loaded?.data && Array.isArray(loaded.data) ? loaded.data : null;
  alarmsMemo = { atMs: now, list };
  return list;
}

export function ingestThreatTypeRequiresAirAlarmGate(threatRaw: string | undefined): boolean {
  const t = String(threatRaw || '').toLowerCase().trim();
  if (!t || NEVER_AIR_ALARM_GATE.has(t)) return false;
  return GATED_THREAT_TYPES.has(t);
}

function districtLabelMatchesActiveAlarms(
  alarms: Alarm[],
  regionHint: string,
  placeHint: string,
): boolean {
  const districts = districtRegionNamesForAlarms(alarms);
  const tryMatch = (a: string, b: string) => {
    const x = normalizeAlarmRegionName(a);
    const y = normalizeAlarmRegionName(b);
    return x.length >= 6 && y.length >= 6 && (x.includes(y) || y.includes(x));
  };
  const placePrefixDistrict = (place: string, districtNorm: string) => {
    const p = normalizeAlarmRegionName(place);
    const d = normalizeAlarmRegionName(districtNorm);
    if (p.length < 6 || d.length < p.length + 3) return false;
    return d.startsWith(p.slice(0, 6));
  };
  for (const d of districts) {
    if (regionHint && tryMatch(regionHint, d)) return true;
    if (placeHint && tryMatch(placeHint, d)) return true;
    if (placeHint && placePrefixDistrict(placeHint, d)) return true;
  }
  return false;
}

function rayonCoveredByDistrictAlarms(alarms: Alarm[], rayonNorm: string | null): boolean {
  if (!rayonNorm) return false;
  const districtNorms = districtRegionNamesForAlarms(alarms);
  for (const d of districtNorms) {
    if (!d) continue;
    if (d === rayonNorm) return true;
    if (d.includes(rayonNorm) || rayonNorm.includes(d)) return true;
  }
  return false;
}

/**
 * Same rule as the red shading on the Leaflet map (`stateAlarmStyle` on `ukraine_oblasts.geojson`
 * + `DistrictAlarmCanvasLayer` on `ukraine_raions_2020.geojson`): point must fall inside an oblast
 * HASC that has an active State alarm, or inside a raion whose normalized `rayon` name matches an
 * active District alarm from `/api/alarms/all`.
 *
 * Outside all oblast polygons (e.g. open sea): **true** (do not gate maritime placements).
 * No alarm payload / API down: **true** (fail-open).
 */
export async function coordsCoveredByActiveAirAlarm(lat: number, lng: number): Promise<boolean> {
  const hasc = findHascContainingPoint(lat, lng);
  if (!hasc) return true;

  const alarms = await alarmsSnapshot();
  if (!alarms || alarms.length === 0) return true;

  const oblastFc = getOblastFeatureCollection();
  const alarmHascs = new Set(hascListForStateAlarms(alarms, oblastFc));
  if (alarmHascs.has(hasc)) return true;

  const rayonNorm = findRayonNormalizedContainingPoint(lat, lng);
  if (rayonCoveredByDistrictAlarms(alarms, rayonNorm)) return true;

  return false;
}

export async function assertAirAlarmGateForIngest(
  marker: Record<string, unknown>,
): Promise<{ ok: true } | { ok: false; reason: string }> {
  if (Boolean(marker.manual)) return { ok: true };
  if (ingestChannelSkipsAirAlarmGate(marker)) return { ok: true };

  const tt = String(marker.threat_type || marker.type || '').toLowerCase();
  if (!ingestThreatTypeRequiresAirAlarmGate(tt)) return { ok: true };

  const lat = Number(marker.lat);
  const lng = Number(marker.lng);
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
    return { ok: false, reason: 'invalid coordinates for air-alarm gate' };
  }

  const covered = await coordsCoveredByActiveAirAlarm(lat, lng);
  if (covered) return { ok: true };

  // Allow high confidence markers even without an official alarm
  const confidence = Number(marker.confidence || 0);
  if (confidence >= 0.9) return { ok: true };

  const alarms = await alarmsSnapshot();
  if (alarms && alarms.length > 0) {
    const oblastFc = getOblastFeatureCollection();
    const alarmHascs = new Set(hascListForStateAlarms(alarms, oblastFc));
    const resolvedRegion = String(marker.region || '').trim();
    const statedOblast = String(marker.oblast || '').trim();
    const regionHints = [...new Set([resolvedRegion, statedOblast].filter(Boolean))];
    for (const h of regionHints) {
      const hascLbl = findOblastHascForRegionLabel(h, oblastFc);
      if (hascLbl && alarmHascs.has(hascLbl)) return { ok: true };
    }
    const placeHint = String(marker.place || marker.location || '').trim();
    for (const h of regionHints.length ? regionHints : ['']) {
      if (districtLabelMatchesActiveAlarms(alarms, h, placeHint)) return { ok: true };
    }
  }

  const hint =
    findHascContainingPoint(lat, lng) ||
    normalizeAlarmRegionName(String(marker.region || marker.oblast || '')) ||
    '?';
  return {
    ok: false,
    reason: `no_active_air_alarm:${hint}`,
  };
}
