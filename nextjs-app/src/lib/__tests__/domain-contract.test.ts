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
import { markerPassesPublicMapRawFilter, parseRawMarkerMessageTimeMs } from '../marker-publication';
import { mapStoreRecordToMarker } from '../map-store-record-to-marker';
import { normalizeAirBalloonThreatType } from '../threat-type-air-balloon';
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
    markerPassesPublicMapRawFilter(marker, {
      minConf: 0.65,
      dualSourceMapGate: false,
      ttlEnabled: true,
      cutoffMs: now - 30 * 60_000,
      hiddenSet: new Set(),
      messageTimeMs: parseRawMarkerMessageTimeMs(marker),
    }),
    false,
  );
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
    markerPassesPublicMapRawFilter(marker, {
      minConf: 0.65,
      dualSourceMapGate: false,
      ttlEnabled: true,
      cutoffMs: now - 30 * 60_000,
      hiddenSet: new Set(),
      messageTimeMs: parseRawMarkerMessageTimeMs(marker),
    }),
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
    markerPassesPublicMapRawFilter(marker, {
      minConf: 0.65,
      dualSourceMapGate: false,
      ttlEnabled: true,
      cutoffMs: now - 30 * 60_000,
      hiddenSet: new Set(),
      messageTimeMs: parseRawMarkerMessageTimeMs(marker),
    }),
    false,
  );
});

test('stale and split-candidate automatic tracks are excluded from public raw map filter', () => {
  for (const trackState of ['stale', 'split_candidate']) {
    const marker = {
      lat: 49.0,
      lng: 32.0,
      confidence: 0.9,
      track_state: trackState,
      ts: new Date(now).toISOString(),
    };
    assert.equal(
      markerPassesPublicMapRawFilter(marker, {
        minConf: 0.65,
        dualSourceMapGate: false,
        ttlEnabled: true,
        cutoffMs: now - 30 * 60_000,
        hiddenSet: new Set(),
        messageTimeMs: parseRawMarkerMessageTimeMs(marker),
      }),
      false,
    );
  }
});

test('low track-confidence automatic marker is excluded instead of dimmed', () => {
  const marker = {
    lat: 49.0,
    lng: 32.0,
    confidence: 0.9,
    track_confidence: 0.49,
    track_state: 'extrapolated',
    ts: new Date(now).toISOString(),
  };
  assert.equal(
    markerPassesPublicMapRawFilter(marker, {
      minConf: 0.65,
      dualSourceMapGate: false,
      ttlEnabled: true,
      cutoffMs: now - 30 * 60_000,
      hiddenSet: new Set(),
      messageTimeMs: parseRawMarkerMessageTimeMs(marker),
    }),
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
    markerPassesPublicMapRawFilter(marker, {
      minConf: 0.65,
      dualSourceMapGate: false,
      ttlEnabled: true,
      cutoffMs: now - 30 * 60_000,
      hiddenSet: new Set(),
      messageTimeMs: parseRawMarkerMessageTimeMs(marker),
    }),
    true,
  );
});

test('dual-source gate hides pending single-source automatic marker', () => {
  const marker = {
    lat: 49.0,
    lng: 32.0,
    confidence: 0.9,
    corroboration_pending: true,
    ts: new Date(now).toISOString(),
  };
  assert.equal(
    markerPassesPublicMapRawFilter(marker, {
      minConf: 0.65,
      dualSourceMapGate: true,
      ttlEnabled: true,
      cutoffMs: now - 30 * 60_000,
      hiddenSet: new Set(),
      messageTimeMs: parseRawMarkerMessageTimeMs(marker),
    }),
    false,
  );
});

test('dual-source gate recomputes single-source observations even without pending flag', () => {
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
    markerPassesPublicMapRawFilter(marker, {
      minConf: 0.65,
      dualSourceMapGate: true,
      ttlEnabled: true,
      cutoffMs: now - 30 * 60_000,
      hiddenSet: new Set(),
      messageTimeMs: parseRawMarkerMessageTimeMs(marker),
    }),
    false,
  );
});

test('dual-source gate allows priority-1 official single-source marker', () => {
  const marker = {
    lat: 47.47,
    lng: 36.25,
    confidence: 0.95,
    observations: [
      { lat: 47.47, lng: 36.25, ts: now - 30_000, source: 'UkraineAlarmSignal', channel_priority: 1 },
    ],
    ts: new Date(now).toISOString(),
  };
  assert.equal(
    markerPassesPublicMapRawFilter(marker, {
      minConf: 0.65,
      dualSourceMapGate: true,
      ttlEnabled: true,
      cutoffMs: now - 30 * 60_000,
      hiddenSet: new Set(),
      messageTimeMs: parseRawMarkerMessageTimeMs(marker),
    }),
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

test('map render profile keeps exact district SVG for mobile and WebView', () => {
  const mobile = resolveMapRenderProfile({
    isEmbed: false,
    userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) Mobile',
    maxTouchPoints: 5,
  });
  const webview = resolveMapRenderProfile({
    isEmbed: true,
    userAgent: 'Mozilla/5.0 (Linux; Android 14) Mobile',
    maxTouchPoints: 5,
  });

  for (const profile of [mobile, webview]) {
    assert.equal(profile.lowInteraction, true);
    assert.equal(profile.svg.loadDetailedDistricts, true);
    assert.equal(profile.svg.loadOblastNames, true);
    assert.equal(profile.svg.allowDistrictGeoJson, false);
    assert.equal(profile.svg.hideDuringInteraction, true);
  }
});

test('map render profile keeps desktop on full alarm SVG contract too', () => {
  const desktop = resolveMapRenderProfile({
    isEmbed: false,
    userAgent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
    maxTouchPoints: 0,
  });

  assert.equal(desktop.kind, 'desktop');
  assert.equal(desktop.lowInteraction, false);
  assert.equal(desktop.svg.loadDetailedDistricts, true);
  assert.equal(desktop.svg.loadOblastNames, true);
  assert.equal(desktop.svg.allowDistrictGeoJson, false);
});
