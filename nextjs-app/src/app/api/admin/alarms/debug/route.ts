import { readFileSync } from 'node:fs';
import path from 'node:path';
import { NextResponse } from 'next/server';
import { requireAdminAuth } from '@/lib/admin/apiAuth';
import { loadAlarms } from '@/lib/alarms-data';
import {
  alarmRegionNameAliases,
  districtRegionIdsForAlarms,
  districtRegionNamesForAlarms,
  findOblastHascForRegionLabel,
  hascListForStateAlarms,
  normalizeAlarmRegionName,
  type OblastFeatureCollection,
} from '@/lib/map/alarm-hasc-filter';
import type { Alarm } from '@/types';

export const dynamic = 'force-dynamic';

type RaionFeatureCollection = {
  type: 'FeatureCollection';
  features: Array<{
    properties?: Record<string, unknown> | null;
  }>;
};

function loadJson<T>(fileName: string): T {
  return JSON.parse(readFileSync(path.join(process.cwd(), 'public', fileName), 'utf8')) as T;
}

function aliasesFor(value: string): string[] {
  return alarmRegionNameAliases(value)
    .map((x) => x.trim())
    .filter(Boolean);
}

function alarmMatchesLabel(alarm: Alarm, label: string): boolean {
  const wanted = new Set(aliasesFor(label).map(normalizeAlarmRegionName));
  const candidates = aliasesFor(alarm.regionName || '').map(normalizeAlarmRegionName);
  return candidates.some((candidate) => wanted.has(candidate));
}

function findMatchingAlarms(alarms: Alarm[], label: string): Alarm[] {
  if (!label) return [];
  return alarms.filter((alarm) => alarmMatchesLabel(alarm, label));
}

function findRaionFeatures(raions: RaionFeatureCollection, label: string) {
  const wanted = new Set(aliasesFor(label).map(normalizeAlarmRegionName));
  return (raions.features || [])
    .filter((feature) => {
      const props = feature.properties || {};
      const labels = [
        props.rayon,
        props.regionName,
        props.name,
        props.NAME_1,
      ].map((x) => normalizeAlarmRegionName(String(x || ''))).filter(Boolean);
      return labels.some((candidate) => wanted.has(candidate));
    })
    .slice(0, 10)
    .map((feature) => feature.properties || {});
}

export async function GET(request: Request) {
  const denied = await requireAdminAuth();
  if (denied) return denied;

  const url = new URL(request.url);
  const region = (url.searchParams.get('region') || url.searchParams.get('q') || '').trim();
  if (!region) {
    return NextResponse.json({ status: 'error', error: 'region query param is required' }, { status: 400 });
  }

  const loaded = await loadAlarms();
  const alarms = loaded?.data || [];
  const oblasts = loadJson<OblastFeatureCollection>('ukraine_oblasts.geojson');
  const raions = loadJson<RaionFeatureCollection>('ukraine_raions_2020.geojson');
  const activeOblastHascs = hascListForStateAlarms(alarms, oblasts);
  const activeDistrictNames = districtRegionNamesForAlarms(alarms);
  const activeDistrictIds = districtRegionIdsForAlarms(alarms);
  const matchedAlarms = findMatchingAlarms(alarms, region);
  const matchingRaions = findRaionFeatures(raions, region);
  const oblastHasc = findOblastHascForRegionLabel(region, oblasts);
  const normalizedAliases = aliasesFor(region).map(normalizeAlarmRegionName);
  const districtActiveByName = normalizedAliases.some((alias) => activeDistrictNames.includes(alias));
  const oblastActiveByHasc = oblastHasc ? activeOblastHascs.includes(oblastHasc) : false;
  const districtAliasCoverage = normalizedAliases.map((alias) => ({
    alias,
    active_by_name: activeDistrictNames.includes(alias),
    matched_active_names: activeDistrictNames.filter((name) => name === alias),
  }));
  const raionCoverage = matchingRaions.map((props) => {
    const labels = [props.rayon, props.regionName, props.name, props.NAME_1]
      .map((x) => String(x || ''))
      .filter(Boolean);
    const normalized = labels.map(normalizeAlarmRegionName).filter(Boolean);
    return {
      labels,
      normalized,
      active_by_name: normalized.some((name) => activeDistrictNames.includes(name)),
      region_id: props.regionId || props.id || props.ID_1 || null,
    };
  });

  return NextResponse.json({
    status: 'ok',
    query: {
      region,
      normalized: normalizeAlarmRegionName(region),
      aliases: aliasesFor(region),
      normalized_aliases: normalizedAliases,
    },
    alarm_snapshot: {
      available: Boolean(loaded),
      age_seconds: loaded?.ageSeconds ?? null,
      active_oblast_hascs: activeOblastHascs,
      active_district_names: activeDistrictNames,
      active_district_ids: activeDistrictIds,
    },
    match: {
      oblast_hasc: oblastHasc,
      oblast_active_by_hasc: oblastActiveByHasc,
      district_active_by_name: districtActiveByName,
      active: oblastActiveByHasc || districtActiveByName || matchedAlarms.some((a) => Boolean(a.activeAlerts?.length)),
      district_alias_coverage: districtAliasCoverage,
      raion_geojson_coverage: raionCoverage,
    },
    matched_alarms: matchedAlarms.map((alarm) => ({
      regionId: alarm.regionId,
      regionType: alarm.regionType,
      regionName: alarm.regionName,
      activeAlerts: alarm.activeAlerts,
      aliases: aliasesFor(alarm.regionName || ''),
    })),
    matching_raion_geojson: matchingRaions,
  });
}
