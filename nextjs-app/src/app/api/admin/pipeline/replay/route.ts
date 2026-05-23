import { spawn } from 'node:child_process';
import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { NextResponse } from 'next/server';
import { requireAdminAuth } from '@/lib/admin/apiAuth';
import { loadHidden, loadSettings } from '@/lib/admin/data';
import { loadAlarms } from '@/lib/alarms-data';
import {
  alarmRegionNameAliases,
  districtRegionNamesForAlarms,
  hascListForStateAlarms,
  normalizeAlarmRegionName,
  type OblastFeatureCollection,
} from '@/lib/map/alarm-hasc-filter';
import {
  explainPublicMapRawFilter,
  parseRawMarkerMessageTimeMs,
} from '@/lib/marker-publication';
import { evaluateMarkerPublication } from '@/lib/public-marker-policy';
import type { Alarm } from '@/types';

export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

type ReplayEntity = Record<string, unknown> & {
  resolve?: Record<string, unknown>;
};

function resolvePythonBinary(): string {
  if (process.env.REPLAY_PYTHON_BIN) return process.env.REPLAY_PYTHON_BIN;
  if (existsSync('/home/neptun/venv/bin/python')) return '/home/neptun/venv/bin/python';
  return 'python3';
}

async function runParserReplay(text: string, channel?: string): Promise<Record<string, unknown>> {
  const script = path.join(process.cwd(), 'worker', 'scripts', 'replay_parse.py');
  const stdout = await new Promise<string>((resolve, reject) => {
    const child = spawn(resolvePythonBinary(), [script], {
      cwd: path.join(process.cwd(), 'worker'),
      stdio: ['pipe', 'pipe', 'pipe'],
      env: {
        ...process.env,
        TELEGRAM_API_ID: process.env.TELEGRAM_API_ID || '12345',
        TELEGRAM_API_HASH: process.env.TELEGRAM_API_HASH || '0123456789abcdef0123456789abcdef',
        QUEUE_DIR: process.env.QUEUE_DIR || '/tmp/neptun-pipeline-replay-queue',
      },
    });
    let out = '';
    let err = '';
    const timer = setTimeout(() => {
      child.kill('SIGKILL');
      reject(new Error('pipeline replay timed out'));
    }, 10_000);

    child.stdout.setEncoding('utf8');
    child.stderr.setEncoding('utf8');
    child.stdout.on('data', (chunk: string) => {
      out += chunk;
      if (out.length > 1024 * 1024) {
        child.kill('SIGKILL');
        reject(new Error('pipeline replay output too large'));
      }
    });
    child.stderr.on('data', (chunk: string) => { err += chunk; });
    child.on('error', (error) => {
      clearTimeout(timer);
      reject(error);
    });
    child.on('close', (code) => {
      clearTimeout(timer);
      if (code === 0) resolve(out);
      else reject(new Error(err || `pipeline replay exited with code ${code}`));
    });
    child.stdin.end(JSON.stringify({ text, channel, resolve: true }));
  });
  return JSON.parse(stdout) as Record<string, unknown>;
}

function loadOblastGeoJson(): OblastFeatureCollection {
  const file = path.join(process.cwd(), 'public', 'ukraine_oblasts.geojson');
  return JSON.parse(readFileSync(file, 'utf8')) as OblastFeatureCollection;
}

function alarmActiveForLabel(label: unknown, alarms: Alarm[]): boolean {
  const labels = alarmRegionNameAliases(String(label || ''))
    .map(normalizeAlarmRegionName)
    .filter(Boolean);
  if (labels.length === 0) return false;
  for (const alarm of alarms) {
    if (!alarm.activeAlerts?.length) continue;
    const candidates = alarmRegionNameAliases(alarm.regionName || '')
      .map(normalizeAlarmRegionName)
      .filter(Boolean);
    if (labels.some((l) => candidates.includes(l))) return true;
  }
  return false;
}

function threatTypeForEntity(entity: ReplayEntity): string {
  const t = String(entity.event_type || '').toLowerCase();
  if (t === 'uav' || t === 'drone' || t === 'shahed') return 'shahed';
  if (t === 'raketa' || t === 'missile' || t === 'pusk') return 'missile';
  return t || 'unknown';
}

function markerForEntity(entity: ReplayEntity, channel: string | undefined, nowMs: number): Record<string, unknown> | null {
  const resolve = entity.resolve || {};
  if (resolve.status !== 'ok') return null;
  const lat = Number(resolve.lat);
  const lng = Number(resolve.lng);
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) return null;
  const isPredictive = resolve.is_predictive === true;
  const confidence = Number(resolve.confidence);
  return {
    id: `replay_${nowMs}_${Math.random().toString(36).slice(2)}`,
    lat,
    lng,
    threat_type: threatTypeForEntity(entity),
    type: threatTypeForEntity(entity),
    place: resolve.place_name || entity.place_name || entity.target_city || '',
    region: resolve.oblast || entity.effective_oblast || entity.oblast || '',
    text: entity.raw_text || '',
    channel_name: channel || 'admin_replay',
    channel_priority: 3,
    confidence: Number.isFinite(confidence) ? confidence : 0.7,
    confidence_0_100: Number.isFinite(confidence) ? Math.round(confidence * 100) : 70,
    created_at_epoch: nowMs,
    last_update_epoch: nowMs,
    count: Number(entity.count) || 1,
    target_lifecycle_state: 'TRACKING',
    target_confidence: Number.isFinite(confidence) ? confidence : 0.7,
    track_state: isPredictive ? 'extrapolated' : 'observed',
    track_confidence: Number.isFinite(confidence) ? confidence : 0.7,
    resolve_status: isPredictive ? 'direction_geocode_fallback' : String(resolve.status || 'ok'),
    placement_mode: isPredictive ? 'target_only_no_current_position' : 'point',
    geocode_tier: isPredictive ? 'target' : 'point',
    source_count: 1,
    event_fingerprint: `replay:${nowMs}:${String(entity.raw_text || '').slice(0, 120)}`,
  };
}

function explainPipelineOutcome(input: {
  marker: Record<string, unknown> | null;
  publication: ReturnType<typeof evaluateMarkerPublication> | null;
  publicMap: ReturnType<typeof explainPublicMapRawFilter> | { passes: false; reason: string; details: Record<string, unknown> };
  tracker: Record<string, unknown> | null;
  oblastAlarm: boolean;
  districtAlarm: boolean;
  resolvedOblast: unknown;
  resolvedRaion: unknown;
}): Record<string, unknown> {
  const reasons: string[] = [];
  let visible = false;
  let blockingStage = 'none';

  if (!input.marker) {
    blockingStage = 'geo';
    reasons.push('entity_not_resolved_to_coordinates');
  } else if (input.publication && input.publication.public !== true) {
    blockingStage = 'publication';
    reasons.push(...input.publication.reasons.map((r) => `publication:${r}`));
  } else if (!input.publicMap.passes) {
    blockingStage = 'public_map_filter';
    reasons.push(`public_map:${input.publicMap.reason}`);
  } else if (input.tracker?.status === 'error') {
    blockingStage = 'tracker';
    reasons.push(`tracker:${String(input.tracker.reason || 'error')}`);
  } else {
    visible = true;
    reasons.push('public_map_passed');
  }

  if (!input.oblastAlarm && !input.districtAlarm) {
    reasons.push('alarm_gate:no_matching_active_oblast_or_district');
  }
  if (input.resolvedOblast) reasons.push(`oblast:${String(input.resolvedOblast)}`);
  if (input.resolvedRaion) reasons.push(`district:${String(input.resolvedRaion)}`);

  return {
    visible_on_public_map: visible,
    blocking_stage: blockingStage,
    reasons,
    recommended_debug: [
      'check marker.resolve_status and placement_mode',
      'check pipeline.publication.reasons',
      'check pipeline.public_map.reason',
      'check pipeline.tracker.classifier and association_hypotheses',
    ],
  };
}

async function analyzeEntity(
  entity: ReplayEntity,
  alarms: Alarm[],
  activeOblastHascs: string[],
  activeDistrictNames: string[],
  channel: string | undefined,
) {
  const settings = loadSettings();
  const hiddenSet = new Set(loadHidden());
  const nowMs = Date.now();
  const marker = markerForEntity(entity, channel, nowMs);
  const entityOblast = entity.effective_oblast || entity.oblast;
  const resolvedOblast = entity.resolve?.oblast;
  const resolvedRaion = entity.resolve?.raion || entity.raion;
  const oblastAlarm = alarmActiveForLabel(resolvedOblast || entityOblast, alarms);
  const districtAlarm = alarmActiveForLabel(resolvedRaion, alarms);
  const publication = marker ? evaluateMarkerPublication(marker, { settings, nowMs }) : null;
  const messageTimeMs = marker ? parseRawMarkerMessageTimeMs(marker) : 0;
  let tracker: Record<string, unknown> | null = null;
  if (marker) {
    const { dryRunMarkerEvidence } = await import('@/lib/tracked-target-store');
    tracker = await dryRunMarkerEvidence(marker);
  }
  const publicMap = marker
    ? explainPublicMapRawFilter(marker, {
        settings,
        ttlEnabled: settings.ttlEnabled !== false,
        cutoffMs: settings.ttlEnabled !== false ? nowMs - (settings.monitorPeriod || 30) * 60_000 : 0,
        hiddenSet,
        messageTimeMs,
      })
    : { passes: false, reason: 'geo_not_resolved', details: {} };

  return {
    ...entity,
    pipeline: {
      alarm_gate: {
        oblast_active: oblastAlarm,
        district_active: districtAlarm,
        active_oblast_hascs: activeOblastHascs,
        active_district_names: activeDistrictNames,
        checked_oblast: resolvedOblast || entityOblast || null,
        checked_district: resolvedRaion || null,
      },
      publication: publication
        ? {
            class: publication.classification,
            public: publication.public,
            score: publication.score,
            reasons: publication.reasons,
            invariant_violations: publication.invariantViolations,
          }
        : null,
      public_map: publicMap,
      tracker,
      marker,
      explain: explainPipelineOutcome({
        marker,
        publication,
        publicMap,
        tracker,
        oblastAlarm,
        districtAlarm,
        resolvedOblast,
        resolvedRaion,
      }),
    },
  };
}

export async function GET(request: Request) {
  const denied = await requireAdminAuth();
  if (denied) return denied;

  const url = new URL(request.url);
  const text = (url.searchParams.get('text') || url.searchParams.get('q') || '').trim();
  const channel = (url.searchParams.get('channel') || '').trim() || undefined;
  if (!text) {
    return NextResponse.json({ status: 'error', error: 'text query param is required' }, { status: 400 });
  }

  try {
    const [replay, loadedAlarms] = await Promise.all([runParserReplay(text, channel), loadAlarms()]);
    const alarms = loadedAlarms?.data || [];
    const oblastGeo = loadOblastGeoJson();
    const activeOblastHascs = hascListForStateAlarms(alarms, oblastGeo);
    const activeDistrictNames = districtRegionNamesForAlarms(alarms);
    const entities = Array.isArray(replay.entities) ? replay.entities as ReplayEntity[] : [];
    return NextResponse.json({
      status: 'ok',
      input: { text, channel },
      alarm_snapshot: {
        available: Boolean(loadedAlarms),
        age_seconds: loadedAlarms?.ageSeconds ?? null,
        active_oblast_hascs: activeOblastHascs,
        active_district_names: activeDistrictNames,
      },
      parser: replay,
      entities: await Promise.all(
        entities.map((entity) => analyzeEntity(entity, alarms, activeOblastHascs, activeDistrictNames, channel)),
      ),
    });
  } catch (error) {
    return NextResponse.json({
      status: 'error',
      error: error instanceof Error ? error.message : String(error),
    }, { status: 500 });
  }
}

export async function POST(request: Request) {
  const denied = await requireAdminAuth();
  if (denied) return denied;

  const body = await request.json().catch(() => ({}));
  const text = typeof body.text === 'string' ? body.text.trim() : '';
  const channel = typeof body.channel === 'string' ? body.channel.trim() : undefined;
  if (!text) {
    return NextResponse.json({ status: 'error', error: 'text is required' }, { status: 400 });
  }
  const req = new Request(`http://local/api/admin/pipeline/replay?text=${encodeURIComponent(text)}${channel ? `&channel=${encodeURIComponent(channel)}` : ''}`, {
    headers: request.headers,
  });
  return GET(req);
}
