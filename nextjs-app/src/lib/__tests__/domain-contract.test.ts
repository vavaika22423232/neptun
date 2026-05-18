import assert from 'node:assert/strict';

import { computeMarkerDisplayPolicy, DEFAULT_MARKER_DISPLAY_POLICY } from '../marker-display-policy';
import {
  decidePositionUpdate,
  decideTickerStep,
  resolveTickerBearing,
  smoothObservedSpeedKmh,
} from '../marker-movement-policy';
import { computeMapModeState } from '../map-mode-state';
import { resolveMapRenderProfile } from '../map/map-render-profile';
import { coalesceMarkerNewEvents } from '../marker-sse-coalesce';
import type { AdminSettings } from '../admin/data';
import {
  explainPublicMapRawFilter,
  markerPassesPublicMapRawFilter,
  parseRawMarkerMessageTimeMs,
} from '../marker-publication';
import { mapStoreRecordToMarker } from '../map-store-record-to-marker';
import { normalizeIngestMotionFields, normalizeIngestMotionPatch } from '../ingest-motion-normalize';
import { normalizeAirBalloonThreatType } from '../threat-type-air-balloon';
import type { Alarm } from '@/types';
import {
  ingestThreatTypeRequiresAirAlarmGate,
} from '../ingest-air-alarm-gate';
import { districtRegionNamesForAlarms, hascListForStateAlarms } from '../map/alarm-hasc-filter';
import { expandMarkersForSwarmDisplay } from '../map/marker-swarm-expand';
import { markersToGeoJSON } from '../map/markers-to-geojson';
import { THREAT_ICONS, THREAT_NAMES } from '@/types';
import type { Marker } from '@/types';

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

function mkAdminSettings(overrides: Partial<AdminSettings> = {}): AdminSettings {
  return {
    monitorPeriod: 30,
    ttlEnabled: true,
    minConfidence: 0.65,
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

function rawMapCtx(marker: Record<string, unknown>, settings: AdminSettings, cutoffMs: number) {
  return {
    settings,
    ttlEnabled: true,
    cutoffMs,
    hiddenSet: new Set<string>(),
    messageTimeMs: parseRawMarkerMessageTimeMs(marker),
  };
}

test('air-alarm ingest gate covers UAV, missiles, ballistic, KAB, strikes (not balloon)', () => {
  assert.equal(ingestThreatTypeRequiresAirAlarmGate('shahed'), true);
  assert.equal(ingestThreatTypeRequiresAirAlarmGate('air_balloon'), false);
  assert.equal(ingestThreatTypeRequiresAirAlarmGate('ballistic'), true);
  assert.equal(ingestThreatTypeRequiresAirAlarmGate('raketa'), true);
  assert.equal(ingestThreatTypeRequiresAirAlarmGate('missile'), true);
  assert.equal(ingestThreatTypeRequiresAirAlarmGate('kab'), true);
  assert.equal(ingestThreatTypeRequiresAirAlarmGate('vibuh'), true);
  assert.equal(ingestThreatTypeRequiresAirAlarmGate('alarm'), false);
  assert.equal(ingestThreatTypeRequiresAirAlarmGate('default'), false);
});

test('multi-count UAV group stays a single map marker without count badge text', () => {
  const marker = {
    id: 'group-1',
    type: 'shahed',
    threat_type: 'shahed',
    location: 'Залісся',
    region: 'Київська область',
    lat: 50.632,
    lng: 30.874,
    count: 4,
    confidence: 0.95,
    resolve_status: 'ok',
    placement_mode: 'point',
    timestamp: new Date(now).toISOString(),
  } as Marker;

  const expanded = expandMarkersForSwarmDisplay([marker]);
  assert.equal(expanded.length, 1);
  assert.equal(expanded[0]?.count, 4);

  const geojson = markersToGeoJSON([marker]);
  assert.equal(geojson.features.length, 1);
  assert.equal(geojson.features[0]?.properties.count, 4);
  assert.equal(geojson.features[0]?.properties.count_label, '');
});

test('state alarm regionId UA-18 maps to Zhytomyr HASC like map oblast fill', () => {
  const fc = {
    type: 'FeatureCollection' as const,
    features: [
      {
        type: 'Feature' as const,
        properties: { HASC_1: 'UA.ZT', NL_NAME_1: 'Житомирська', NAME_1: 'Zhytomyr' },
        geometry: { type: 'Polygon' as const, coordinates: [] as number[][][] },
      },
    ],
  };
  const alarms: Alarm[] = [
    {
      regionId: 'UA-18',
      regionType: 'State',
      regionName: '',
      activeAlerts: [{ type: 'AIR' }],
    },
  ];
  assert.ok(hascListForStateAlarms(alarms, fc).includes('UA.ZT'));
});

test('renamed Samarskyi district alarm also covers legacy Novomoskovskyi raion polygons', () => {
  const alarms: Alarm[] = [
    {
      regionId: '43',
      regionType: 'District',
      regionName: 'Самарівський район',
      activeAlerts: [{ type: 'AIR' }],
    },
  ];

  const districts = districtRegionNamesForAlarms(alarms);
  assert.ok(districts.includes('самарівськии раион'));
  assert.ok(districts.includes('новомосковськии раион'));
});

test('district alarm names normalize apostrophe variants used by API and GeoJSON', () => {
  const alarms: Alarm[] = [
    {
      regionId: '42',
      regionType: 'District',
      regionName: 'Кам’янський район',
      activeAlerts: [{ type: 'AIR' }],
    },
    {
      regionId: '123',
      regionType: 'District',
      regionName: 'Куп’янський район',
      activeAlerts: [{ type: 'AIR' }],
    },
  ];

  const districts = districtRegionNamesForAlarms(alarms);
  assert.ok(districts.includes('камянськии раион'));
  assert.ok(districts.includes('купянськии раион'));
});

test('renamed district alarms cover legacy 2020 raion GeoJSON names', () => {
  const alarms: Alarm[] = [
    {
      regionId: '60',
      regionType: 'District',
      regionName: 'Звягельський район',
      activeAlerts: [{ type: 'AIR' }],
    },
    {
      regionId: 'UA-07-02',
      regionType: 'District',
      regionName: 'Володимирський район',
      activeAlerts: [{ type: 'AIR' }],
    },
    {
      regionId: 'UA-46-05',
      regionType: 'District',
      regionName: 'Шептицький район',
      activeAlerts: [{ type: 'AIR' }],
    },
  ];

  const districts = districtRegionNamesForAlarms(alarms);
  assert.ok(districts.includes('новоград-волинськии раион'));
  assert.ok(districts.includes('володимир-волинськии раион'));
  assert.ok(districts.includes('червоноградськии раион'));
});

test('air balloon wording is not left as shahed/uav', () => {
  const marker: Record<string, unknown> = {
    threat_type: 'shahed',
    text: 'Зонд курсом на Черкаси',
  };
  normalizeAirBalloonThreatType(marker);
  assert.equal(marker.threat_type, 'air_balloon');
});

test('low confidence marker is excluded from public raw map filter', () => {
  const marker = {
    lat: 49.0,
    lng: 32.0,
    confidence: 0.31,
    ts: new Date(now).toISOString(),
  };
  assert.equal(
    markerPassesPublicMapRawFilter(
      marker,
      rawMapCtx(marker, mkAdminSettings({ dualSourceMapGate: false }), now - 30 * 60_000),
    ),
    false,
  );
});

test('public raw map filter explains low-confidence exclusion', () => {
  const marker = {
    lat: 49.0,
    lng: 32.0,
    confidence: 0.31,
    ts: new Date(now).toISOString(),
  };
  const decision = explainPublicMapRawFilter(
    marker,
    rawMapCtx(marker, mkAdminSettings({ dualSourceMapGate: false }), now - 30 * 60_000),
  );
  assert.equal(decision.passes, false);
  assert.equal(decision.reason, 'publication_not_public');
});

test('fresh high-confidence V3 UAV tracking target passes public raw filter as radar provisional', () => {
  const marker = {
    id: 'target-provisional',
    track_id: 'target-provisional',
    lat: 49.0,
    lng: 32.0,
    threat_type: 'shahed',
    place: 'Черкаси',
    region: 'Черкаська область',
    confidence: 0.7,
    target_confidence: 0.92,
    target_lifecycle_state: 'TRACKING',
    track_state: 'observed',
    track_confidence: 0.7,
    source_count: 1,
    observations: [{ lat: 49.0, lng: 32.0, ts: now - 90_000, source: 'trusted-a' }],
    channel_priority: 3,
    resolve_status: 'ok',
    placement_mode: 'point',
    created_at_epoch: now - 90_000,
    last_update_epoch: now - 90_000,
  };
  assert.equal(
    markerPassesPublicMapRawFilter(
      marker,
      rawMapCtx(marker, mkAdminSettings({ dualSourceMapGate: true, minConfidenceUav: 0.45 }), now - 30 * 60_000),
    ),
    true,
  );
  const decision = explainPublicMapRawFilter(
    marker,
    rawMapCtx(marker, mkAdminSettings({ dualSourceMapGate: true, minConfidenceUav: 0.45 }), now - 30 * 60_000),
  );
  assert.equal(decision.passes, true);
  assert.equal(decision.reason, 'public');
});

test('fresh high-confidence extrapolated V3 UAV stays visible despite decayed visual confidence', () => {
  const marker = {
    id: 'target-provisional-extrapolated',
    track_id: 'target-provisional-extrapolated',
    lat: 49.03,
    lng: 32.06,
    threat_type: 'shahed',
    place: 'Черкаси',
    region: 'Черкаська область',
    confidence: 0.36,
    target_confidence: 0.93,
    target_lifecycle_state: 'TRACKING',
    track_state: 'extrapolated',
    track_confidence: 0.31,
    source_count: 1,
    observations: [{ lat: 49.0, lng: 32.0, ts: now - 15 * 60_000, source: 'trusted-a' }],
    channel_priority: 3,
    resolve_status: 'ok',
    placement_mode: 'point',
    created_at_epoch: now - 16 * 60_000,
    last_update_epoch: now - 15 * 60_000,
  };
  assert.equal(
    markerPassesPublicMapRawFilter(
      marker,
      rawMapCtx(marker, mkAdminSettings({ dualSourceMapGate: true, minConfidenceUav: 0.45 }), now - 30 * 60_000),
    ),
    true,
  );
});

test('fresh confirmed observed UAV track with moderate confidence passes public raw filter', () => {
  const marker = {
    id: 'target-confirmed-observed',
    track_id: 'target-confirmed-observed',
    lat: 49.0,
    lng: 32.0,
    threat_type: 'shahed',
    place: 'Черкаси',
    region: 'Черкаська область',
    confidence: 0.75,
    target_confidence: 0.75,
    target_lifecycle_state: 'CONFIRMED',
    track_state: 'observed',
    track_confidence: 0.72,
    source_count: 1,
    observations: [{ lat: 49.0, lng: 32.0, ts: now - 60_000, source: 'trusted-a' }],
    channel_priority: 3,
    resolve_status: 'ok',
    placement_mode: 'point',
    created_at_epoch: now - 60_000,
    last_update_epoch: now - 60_000,
  };
  const decision = explainPublicMapRawFilter(
    marker,
    rawMapCtx(marker, mkAdminSettings({ dualSourceMapGate: false, minConfidenceUav: 0.45 }), now - 30 * 60_000),
  );
  assert.equal(decision.passes, true);
  assert.equal(decision.reason, 'public');
});

test('admin hidden marker suppresses nearby ticker-shifted same-text marker', () => {
  const marker = {
    lat: 49.012,
    lng: 32.018,
    confidence: 0.92,
    threat_type: 'shahed',
    text: 'Шахед курсом на Черкаси',
    ts: new Date(now).toISOString(),
  };
  const ctx = rawMapCtx(marker, mkAdminSettings({ dualSourceMapGate: false }), now - 30 * 60_000);
  ctx.hiddenSet = new Set(['49,32|Шахед курсом на Черкаси|auto']);
  assert.equal(markerPassesPublicMapRawFilter(marker, ctx), false);
});

test('ambiguous automatic geocode is kept off the public map', () => {
  const marker = {
    lat: 49.0,
    lng: 32.0,
    confidence: 0.92,
    threat_type: 'shahed',
    place: 'Черкаси',
    geocode_tier: 'multi',
    candidates_count: 3,
    ts: new Date(now).toISOString(),
  };
  assert.equal(
    markerPassesPublicMapRawFilter(
      marker,
      rawMapCtx(marker, mkAdminSettings({ dualSourceMapGate: false }), now - 30 * 60_000),
    ),
    false,
  );
});

test('non-place labels from parser are kept off the public map', () => {
  const marker = {
    lat: 46.45,
    lng: 31.7,
    confidence: 0.92,
    threat_type: 'shahed',
    place: 'воду',
    ts: new Date(now).toISOString(),
  };
  assert.equal(
    markerPassesPublicMapRawFilter(
      marker,
      rawMapCtx(marker, mkAdminSettings({ dualSourceMapGate: false }), now - 30 * 60_000),
    ),
    false,
  );
});

test('coarse automatic placements are kept off the public map', () => {
  const marker = {
    lat: 49.0,
    lng: 32.0,
    confidence: 0.92,
    threat_type: 'shahed',
    place: 'Черкаська область',
    placement_mode: 'approximate',
    resolve_status: 'oblast_fallback',
    ts: new Date(now).toISOString(),
  };
  assert.equal(
    markerPassesPublicMapRawFilter(
      marker,
      rawMapCtx(marker, mkAdminSettings({ dualSourceMapGate: false }), now - 30 * 60_000),
    ),
    false,
  );
});

test('Chișinău-area coords excluded from public map (loose ingest bbox overlaps Moldova)', () => {
  const marker = {
    lat: 47.0105,
    lng: 28.8578,
    confidence: 0.92,
    threat_type: 'shahed',
    ts: new Date(now).toISOString(),
  };
  assert.equal(
    markerPassesPublicMapRawFilter(
      marker,
      rawMapCtx(marker, mkAdminSettings({ dualSourceMapGate: false }), now - 30 * 60_000),
    ),
    false,
  );
});

test('western Black Sea point without evidence stays off the public marker feed', () => {
  const marker = {
    lat: 46.2,
    lng: 31.4,
    confidence: 0.92,
    threat_type: 'shahed',
    ts: new Date(now).toISOString(),
  };
  assert.equal(
    markerPassesPublicMapRawFilter(
      marker,
      rawMapCtx(marker, mkAdminSettings({ dualSourceMapGate: false }), now - 30 * 60_000),
    ),
    false,
  );
});

test('Odesa city alarm passes public filter even though coords fall inside maritime bbox', () => {
  // Odesa: lat=46.483 < 46.7 guard, inside maritime bbox — but place='Одеса' is land evidence
  const marker = {
    lat: 46.483,
    lng: 30.723,
    place: 'Одеса',
    region: 'Одеська область',
    confidence: 0.95,
    threat_type: 'shahed',
    source_count: 2,
    observations: [{ source: 'ch1' }, { source: 'ch2' }],
    ts: new Date(now).toISOString(),
    resolve_status: 'ok',
    placement_mode: 'point',
    geocode_tier: 'point',
  };
  assert.equal(
    markerPassesPublicMapRawFilter(
      marker,
      rawMapCtx(marker, mkAdminSettings({ dualSourceMapGate: false }), now - 30 * 60_000),
    ),
    true,
    'Odesa city should pass — land place evidence exempts it from maritime block',
  );
});

test('Kherson city alarm passes public filter despite being below lat=46.7 maritime guard', () => {
  const marker = {
    lat: 46.64,
    lng: 32.6,
    place: 'Херсон',
    region: 'Херсонська область',
    confidence: 0.95,
    threat_type: 'shahed',
    source_count: 2,
    observations: [{ source: 'ch1' }, { source: 'ch2' }],
    ts: new Date(now).toISOString(),
    resolve_status: 'ok',
    placement_mode: 'point',
    geocode_tier: 'point',
  };
  assert.equal(
    markerPassesPublicMapRawFilter(
      marker,
      rawMapCtx(marker, mkAdminSettings({ dualSourceMapGate: false }), now - 30 * 60_000),
    ),
    true,
    'Kherson city should pass — land place evidence exempts it from maritime block',
  );
});

test('Black Sea maritime approach with place="Чорне море" passes public filter', () => {
  const marker = {
    lat: 45.84,
    lng: 30.8,
    place: 'Чорне море',
    region: '',
    confidence: 0.82,
    threat_type: 'shahed',
    source_count: 2,
    observations: [{ source: 'ch1' }, { source: 'ch2' }],
    ts: new Date(now).toISOString(),
    resolve_status: 'maritime_approach',
    placement_mode: 'point',
    geocode_tier: 'point',
  };
  assert.equal(
    markerPassesPublicMapRawFilter(
      marker,
      rawMapCtx(marker, mkAdminSettings({ dualSourceMapGate: false }), now - 30 * 60_000),
    ),
    true,
    'Maritime approach with "Чорне море" has maritime evidence and should pass',
  );
});

test('UAV below verified-public confidence stays off public even when admin floor is relaxed', () => {
  const marker = {
    lat: 49.0,
    lng: 32.0,
    threat_type: 'shahed',
    confidence: 0.62,
    ts: new Date(now).toISOString(),
  };
  const relaxed = mkAdminSettings({ dualSourceMapGate: false, minConfidence: 0.65, minConfidenceUav: 0.6 });
  assert.equal(
    markerPassesPublicMapRawFilter(marker, rawMapCtx(marker, relaxed, now - 30 * 60_000)),
    false,
  );
  const strict = mkAdminSettings({ dualSourceMapGate: false, minConfidence: 0.65 });
  assert.equal(
    markerPassesPublicMapRawFilter(marker, rawMapCtx(marker, strict, now - 30 * 60_000)),
    false,
  );
});

test('ingest clamps absurd UAV speed to motion profile max', () => {
  const marker: Record<string, unknown> = { threat_type: 'shahed', speed_kmh: 900 };
  normalizeIngestMotionFields(marker);
  assert.equal(marker.speed_kmh, 350);
});

test('ingest motion patch clamps speed_kmh on partial update', () => {
  const updates: Record<string, unknown> = { speed_kmh: 500 };
  normalizeIngestMotionPatch(updates, 'shahed');
  assert.equal(updates.speed_kmh, 350);
});

test('blocked placement mode is excluded from public raw map filter', () => {
  const marker = {
    lat: 46.5,
    lng: 31.8,
    confidence: 0.9,
    placement_mode: 'sea_context_mismatch',
    ts: new Date(now).toISOString(),
  };
  assert.equal(
    markerPassesPublicMapRawFilter(
      marker,
      rawMapCtx(marker, mkAdminSettings({ dualSourceMapGate: false }), now - 30 * 60_000),
    ),
    false,
  );
});

test('lost automatic track is excluded from public raw map filter', () => {
  const marker = {
    lat: 49.0,
    lng: 32.0,
    confidence: 0.9,
    track_state: 'lost',
    ts: new Date(now).toISOString(),
  };
  assert.equal(
    markerPassesPublicMapRawFilter(
      marker,
      rawMapCtx(marker, mkAdminSettings({ dualSourceMapGate: false }), now - 30 * 60_000),
    ),
    false,
  );
});

test('split-candidate automatic track is excluded from public raw map filter', () => {
  const marker = {
    lat: 49.0,
    lng: 32.0,
    confidence: 0.9,
    track_state: 'split_candidate',
    ts: new Date(now).toISOString(),
  };
  assert.equal(
    markerPassesPublicMapRawFilter(
      marker,
      rawMapCtx(marker, mkAdminSettings({ dualSourceMapGate: false }), now - 30 * 60_000),
    ),
    false,
  );
});

test('stale automatic track is not public under verified-marker policy', () => {
  const marker = {
    lat: 49.0,
    lng: 32.0,
    confidence: 0.9,
    track_state: 'stale',
    track_confidence: 0.25,
    ts: new Date(now).toISOString(),
  };
  assert.equal(
    markerPassesPublicMapRawFilter(
      marker,
      rawMapCtx(marker, mkAdminSettings({ dualSourceMapGate: false }), now - 30 * 60_000),
    ),
    false,
  );
});

test('unconfirmed extrapolated track is not public under verified-marker policy', () => {
  const marker = {
    lat: 49.0,
    lng: 32.0,
    confidence: 0.9,
    track_confidence: 0.49,
    track_state: 'extrapolated',
    ts: new Date(now).toISOString(),
  };
  assert.equal(
    markerPassesPublicMapRawFilter(
      marker,
      rawMapCtx(marker, mkAdminSettings({ dualSourceMapGate: false }), now - 30 * 60_000),
    ),
    false,
  );
});

test('observed track with very low motion confidence is still excluded', () => {
  const marker = {
    lat: 49.0,
    lng: 32.0,
    confidence: 0.9,
    track_confidence: 0.49,
    track_state: 'observed',
    ts: new Date(now).toISOString(),
  };
  assert.equal(
    markerPassesPublicMapRawFilter(
      marker,
      rawMapCtx(marker, mkAdminSettings({ dualSourceMapGate: false }), now - 30 * 60_000),
    ),
    false,
  );
});

test('manual lost marker is still allowed through public raw map filter', () => {
  const marker = {
    lat: 49.0,
    lng: 32.0,
    confidence: 0.9,
    track_state: 'lost',
    manual: true,
    ts: new Date(now).toISOString(),
  };
  assert.equal(
    markerPassesPublicMapRawFilter(
      marker,
      rawMapCtx(marker, mkAdminSettings({ dualSourceMapGate: false }), now - 30 * 60_000),
    ),
    true,
  );
});

test('direct single-source automatic marker is not public without verified evidence', () => {
  const marker = {
    lat: 49.0,
    lng: 32.0,
    confidence: 0.9,
    corroboration_pending: true,
    ts: new Date(now).toISOString(),
  };
  assert.equal(
    markerPassesPublicMapRawFilter(
      marker,
      rawMapCtx(marker, mkAdminSettings({ dualSourceMapGate: true }), now - 30 * 60_000),
    ),
    false,
  );
});

test('same-source observations are not enough for verified public marker', () => {
  const marker = {
    lat: 48.9,
    lng: 36.7,
    confidence: 0.95,
    observations: [
      { lat: 48.9, lng: 36.7, ts: now - 60_000, source: 'povitryanatrivogaaa' },
      { lat: 48.91, lng: 36.71, ts: now - 30_000, source: 'povitryanatrivogaaa' },
    ],
    ts: new Date(now).toISOString(),
  };
  assert.equal(
    markerPassesPublicMapRawFilter(
      marker,
      rawMapCtx(marker, mkAdminSettings({ dualSourceMapGate: true }), now - 30 * 60_000),
    ),
    false,
  );
});

test('dual-source gate allows priority-1 official single-source marker', () => {
  const marker = {
    lat: 47.47,
    lng: 36.25,
    confidence: 0.95,
    threat_type: 'shahed',
    place: 'Запоріжжя',
    placement_mode: 'point',
    resolve_status: 'ok',
    observations: [
      { lat: 47.47, lng: 36.25, ts: now - 30_000, source: 'UkraineAlarmSignal', channel_priority: 1 },
    ],
    ts: new Date(now).toISOString(),
  };
  assert.equal(
    markerPassesPublicMapRawFilter(
      marker,
      rawMapCtx(marker, mkAdminSettings({ dualSourceMapGate: true }), now - 30 * 60_000),
    ),
    true,
  );
});

test('two recent observations produce corroborated point display', () => {
  const marker: Marker = {
    id: 'trk-test',
    lat: 49.0,
    lng: 32.0,
    threat_type: 'shahed',
    observations: [
      { lat: 49.0, lng: 32.0, ts: now - 60_000, source: 'channel-a' },
      { lat: 49.02, lng: 32.01, ts: now - 30_000, source: 'channel-b' },
    ],
  };
  const policy = computeMarkerDisplayPolicy(marker, {
    ...DEFAULT_MARKER_DISPLAY_POLICY,
    corroborationMinDistinctSources: 2,
  });
  assert.equal(policy.display_class, 'corroborated_point');
  assert.equal(policy.show_precise_pin, true);
});

test('same-channel observations do not produce corroborated point display', () => {
  const marker: Marker = {
    id: 'trk-single-source',
    lat: 48.9,
    lng: 36.7,
    threat_type: 'shahed',
    observations: [
      { lat: 48.9, lng: 36.7, ts: now - 60_000, source: 'channel-a' },
      { lat: 48.91, lng: 36.71, ts: now - 30_000, source: 'channel-a' },
    ],
  };
  const policy = computeMarkerDisplayPolicy(marker, {
    ...DEFAULT_MARKER_DISPLAY_POLICY,
    corroborationMinDistinctSources: 2,
  });
  assert.equal(policy.display_class, 'region_signal');
  assert.equal(policy.show_precise_pin, false);
});

test('predictive marker with trajectory is shown as corridor or bearing', () => {
  const marker: Marker = {
    id: 'predictive-test',
    lat: 49.0,
    lng: 32.0,
    threat_type: 'shahed',
    placement_mode: 'predictive',
    trajectory: {
      start: [49.0, 32.0],
      end: [49.5, 33.0],
      predicted: true,
      source: 'direction',
    },
  };
  const policy = computeMarkerDisplayPolicy(marker, DEFAULT_MARKER_DISPLAY_POLICY);
  assert.equal(policy.display_class, 'corridor_or_bearing');
  assert.equal(policy.show_precise_pin, false);
});

test('marker_new SSE bursts coalesce to refresh instead of dropping markers', () => {
  assert.deepEqual(coalesceMarkerNewEvents([]), null);
  assert.equal(coalesceMarkerNewEvents([{ id: 'a' }])?.type, 'marker_new');
  const burst = coalesceMarkerNewEvents([{ id: 'a' }, { id: 'b' }, { id: 'c' }]);
  assert.equal(burst?.type, 'markers_refresh');
  assert.deepEqual(burst?.data, { batch: true, count: 3 });
});

test('public type contract includes air balloon icon and label', () => {
  assert.equal(THREAT_ICONS.air_balloon, 'icon_air_balloon.svg');
  assert.match(THREAT_NAMES.air_balloon, /Повітряна куля/);
});

test('map store projection preserves track lifecycle fields', () => {
  const marker = mapStoreRecordToMarker({
    id: 'm1',
    track_id: 'trk1',
    lat: 49,
    lng: 32,
    threat_type: 'shahed',
    track_state: 'extrapolated',
    track_confidence: 0.52,
    motion_reason: 'motion_extrapolated',
    last_observation_epoch: now - 90_000,
    geo_decision_reason: 'accepted_point',
    geocode_source: 'gazetteer',
  });

  assert.equal(marker.track_state, 'extrapolated');
  assert.equal(marker.track_confidence, 0.52);
  assert.equal(marker.motion_reason, 'motion_extrapolated');
  assert.equal(marker.last_observation_epoch, now - 90_000);
  assert.equal(marker.geo_decision_reason, 'accepted_point');
  assert.equal(marker.geocode_source, 'gazetteer');
});

test('map store projection keeps rejected evidence separate from observations', () => {
  const marker = mapStoreRecordToMarker({
    id: 'm2',
    lat: 49,
    lng: 32,
    threat_type: 'shahed',
    observations: [{ lat: 49, lng: 32, ts: now - 60_000, source: 'accepted' }],
    rejected_observations: [{
      lat: 50.7,
      lng: 30.5,
      ts: now,
      source: 'weak-channel',
      reason: 'teleport_blocked_split_candidate',
      confidence: 0.4,
    }],
  });

  assert.equal(marker.observations?.length, 1);
  assert.equal(marker.rejected_observations?.length, 1);
  assert.equal(marker.rejected_observations?.[0]?.reason, 'teleport_blocked_split_candidate');
  assert.equal(marker.rejected_observations?.[0]?.lat, 50.7);
});

test('movement policy rejects stale observations without moving the pin', () => {
  const decision = decidePositionUpdate({
    existingLat: 49,
    existingLng: 32,
    newLat: 49.1,
    newLng: 32.1,
    threatType: 'shahed',
    currentSpeedKmh: 180,
    existingConfidence: 0.9,
    incomingConfidence: 0.9,
    lastObservationTs: now,
    newObservationTs: now - 60_000,
    nowMs: now,
  });
  assert.equal(decision.action, 'hold_position');
  assert.equal(decision.reason, 'stale_observation');
});

test('movement policy holds weak low-confidence geocode jumps', () => {
  const decision = decidePositionUpdate({
    existingLat: 49,
    existingLng: 32,
    newLat: 49.04,
    newLng: 32,
    threatType: 'shahed',
    currentSpeedKmh: 180,
    existingConfidence: 0.82,
    incomingConfidence: 0.35,
    lastObservationTs: now - 60_000,
    newObservationTs: now,
    nowMs: now,
  });
  assert.equal(decision.action, 'hold_position');
  assert.equal(decision.reason, 'weak_geo_hold');
});

test('observed speed smoothing ignores impossible shahed speed', () => {
  const speed = smoothObservedSpeedKmh({
    prev: { lat: 49, lng: 32 },
    curr: { lat: 50, lng: 32 },
    prevTs: now - 60_000,
    currTs: now,
    threatType: 'shahed',
    nowMs: now,
  });
  assert.equal(speed, null);
});

test('ticker prefers motion bearing and stops near target', () => {
  assert.equal(resolveTickerBearing({ course_bearing: 90, ticker_bearing: 45 }), 45);
  const tick = decideTickerStep({
    nowMs: now,
    tickIntervalMs: 15_000,
    marker: {
      lat: 49,
      lng: 32,
      threat_type: 'missile',
      speed_kmh: 900,
      ticker_bearing: 90,
      observations: [{ lat: 49, lng: 31.98, ts: now - 30_000 }],
      trajectory: { end: [49, 32.03] },
    },
  });
  assert.equal(tick.shouldTick, false);
  assert.equal(tick.reason, 'near_target');
});

test('map mode keeps mobile first-fit SVG-only until user zooms', () => {
  const initial = computeMapModeState({
    zoom: 5.4,
    isMobile: true,
    revealed: false,
    zoomAfterFit: 5.4,
    revealZoomEps: 0.08,
    desktopFadeStart: 7,
    desktopFadeEnd: 8,
    mobileFadeStart: 5,
    mobileFadeEnd: 8.5,
  });
  assert.equal(initial.mode, 'svg_only');
  assert.equal(initial.tileOpacity, 0);
  assert.equal(initial.revealed, false);

  const afterPinch = computeMapModeState({
    zoom: 5.55,
    isMobile: true,
    revealed: false,
    zoomAfterFit: 5.4,
    revealZoomEps: 0.08,
    desktopFadeStart: 7,
    desktopFadeEnd: 8,
    mobileFadeStart: 5,
    mobileFadeEnd: 8.5,
  });
  assert.equal(afterPinch.revealed, true);
  assert.equal(afterPinch.mode, 'hybrid_fade');
});

test('map mode fades desktop SVG to tiles across zoom band', () => {
  const low = computeMapModeState({
    zoom: 6.5,
    isMobile: false,
    revealed: true,
    zoomAfterFit: null,
    revealZoomEps: 0.08,
    desktopFadeStart: 7,
    desktopFadeEnd: 8,
    mobileFadeStart: 5,
    mobileFadeEnd: 8.5,
  });
  const high = computeMapModeState({
    zoom: 8,
    isMobile: false,
    revealed: true,
    zoomAfterFit: null,
    revealZoomEps: 0.08,
    desktopFadeStart: 7,
    desktopFadeEnd: 8,
    mobileFadeStart: 5,
    mobileFadeEnd: 8.5,
  });
  assert.equal(low.mode, 'svg_only');
  assert.equal(high.mode, 'tiles_primary');
  assert.equal(high.svgOpacity, 0);
});

test('map render profile uses same vector basemap on mobile browser as on desktop', () => {
  const mobile = resolveMapRenderProfile({
    isEmbed: false,
    userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) Mobile',
    maxTouchPoints: 5,
  });

  assert.equal(mobile.kind, 'mobile');
  assert.equal(mobile.basemap, 'rasterVectorDark');
  assert.equal(mobile.lowTileMode, false);
  assert.equal(mobile.maxZoom, 19);
  assert.equal(mobile.tile.detectRetina, true);
  assert.equal(mobile.lowInteraction, true);
  assert.equal(mobile.svg.loadDetailedDistricts, true);
  assert.equal(mobile.svg.loadOblastNames, true);
  assert.equal(mobile.svg.allowDistrictGeoJson, false);
  assert.equal(mobile.svg.hideDuringInteraction, true);
});

test('in-app WebView (?embed=1) uses same vector basemap as desktop site', () => {
  const webview = resolveMapRenderProfile({
    isEmbed: true,
    userAgent: 'Mozilla/5.0 (Linux; Android 14) Mobile',
    maxTouchPoints: 5,
  });

  assert.equal(webview.kind, 'webview');
  assert.equal(webview.basemap, 'rasterVectorDark');
  assert.equal(webview.lowTileMode, false);
  assert.equal(webview.maxZoom, 19);
  assert.equal(webview.lowInteraction, true);
  assert.equal(webview.tile.detectRetina, true);
  assert.equal(webview.svg.loadDetailedDistricts, true);
  assert.equal(webview.svg.loadOblastNames, true);
  assert.equal(webview.svg.allowDistrictGeoJson, false);
  assert.equal(webview.svg.hideDuringInteraction, true);
});

test('map render profile keeps desktop on full alarm SVG contract too', () => {
  const desktop = resolveMapRenderProfile({
    isEmbed: false,
    userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
    maxTouchPoints: 0,
  });

  assert.equal(desktop.kind, 'desktop');
  assert.equal(desktop.basemap, 'rasterVectorDark');
  assert.equal(desktop.lowTileMode, false);
  assert.equal(desktop.lowInteraction, false);
  assert.equal(desktop.svg.loadDetailedDistricts, true);
  assert.equal(desktop.svg.loadOblastNames, true);
  assert.equal(desktop.svg.allowDistrictGeoJson, false);
});
