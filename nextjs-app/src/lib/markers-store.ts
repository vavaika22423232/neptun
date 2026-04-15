/**
 * In-memory markers store with Redis as shared source of truth.
 *
 * Architecture (PM2 cluster-safe + standalone-safe):
 * - On boot, loads messages.json from disk into memory AND Redis.
 * - `/api/ingest` POST/PATCH mutates Redis + local array + disk.
 * - `/api/ingest/batch` uses deferred persistence: N in-memory updates, then one Redis + disk write.
 * - Every 2 seconds, ALL workers poll Redis and update their local `_messages[]`.
 * - `/api/data` GET reads ONLY from memory — zero file I/O on the hot path.
 *
 * Redis ensures:
 * 1. All PM2 workers see the same markers
 * 2. instrumentation.ts and API route module instances share data
 * 3. Markers survive deploys/restarts (Redis + disk backup)
 */

import fsp from 'fs/promises';
import fs from 'fs';
import path from 'path';
import crypto from 'crypto';
import { getRedis, redisGet, isRedisDisabledInThisProcess } from './redis';
import { clearMarkerDerivedApiCachesLocal, invalidateMarkerDerivedCaches } from './cache';
import { loadSettings } from './admin/data';
import { broadcastSSE } from '@/lib/chat-sse-stream';
import { attachDisplayPolicyToPayload } from '@/lib/marker-broadcast-enrich';
import { ingestShouldBroadcastMarker } from '@/lib/ingest-confidence-gate';
import { recordHasPhantomAvia } from '@/lib/corroboration-public-gate';

// ── Config ───────────────────────────────────────────────────────────────────
const DATA_DIR = process.env.DATA_DIR || '/data';
const MESSAGES_FILE = path.join(DATA_DIR, 'messages.json');
const FALLBACK_MESSAGES_FILE = path.resolve(process.cwd(), '..', 'messages.json');
const MAX_MESSAGES = 500;
const RETENTION_HOURS_FALLBACK = 3; // absolute ceiling if admin settings unavailable
const MY_PID = process.pid;

const REDIS_MARKERS_KEY = 'markers:all';
const REDIS_VERSION_KEY = 'markers:version'; // incremented on every write
const REDIS_MARKERS_TTL = 7200; // 2 hours — refreshed on every write
const POLL_INTERVAL = 12_000; // 12s — poll Redis for cross-worker marker sync (less CPU than 5s × N workers)

/** When >0, ingest mutations skip Redis/disk until `endMarkerIngestBatch()` (single flush). */
let _markerPersistDeferDepth = 0;

/** Bust marker-derived API caches while batch is open — RAM already updated, Redis not yet. */
function invalidateDerivedCachesIfDeferred(): void {
  if (_markerPersistDeferDepth > 0) {
    // Local only — Redis not flushed yet; do not publish (other workers would still have stale Redis).
    clearMarkerDerivedApiCachesLocal();
  }
}

// ── Shared state via globalThis ──────────────────────────────────────────────
// Next.js standalone mode creates SEPARATE module instances for instrumentation.ts
// and API route handlers. Module-level variables (let/const) are NOT shared.
// globalThis IS shared within the same Node.js process, so we use it to ensure
// instrumentation (which starts polling) and API routes (which read markers)
// see the same data.

interface MarkerStoreState {
  messages: Record<string, unknown>[];
  initialized: boolean;
  initPromise: Promise<void> | null;
  lastIngestTime: number;
  pollTimer: ReturnType<typeof setInterval> | null;
  lastVersion: number;
  writeLock: Promise<void>;
}

const GLOBAL_KEY = '__neptun_marker_store__';

function getState(): MarkerStoreState {
  if (!(globalThis as Record<string, unknown>)[GLOBAL_KEY]) {
    (globalThis as Record<string, unknown>)[GLOBAL_KEY] = {
      messages: [],
      initialized: false,
      initPromise: null,
      lastIngestTime: 0,
      pollTimer: null,
      lastVersion: 0,
      writeLock: Promise.resolve(),
    } as MarkerStoreState;
  }
  return (globalThis as Record<string, unknown>)[GLOBAL_KEY] as MarkerStoreState;
}

// Write lock to prevent concurrent disk writes
function withWriteLock<T>(fn: () => Promise<T>): Promise<T> {
  const state = getState();
  const prev = state.writeLock;
  let resolve!: () => void;
  state.writeLock = new Promise<void>((r) => { resolve = r; });
  return prev.then(fn).finally(() => resolve());
}

// ── File resolution ──────────────────────────────────────────────────────────
function resolveFilePath(): string {
  if (fs.existsSync(MESSAGES_FILE)) return MESSAGES_FILE;
  if (fs.existsSync(FALLBACK_MESSAGES_FILE)) return FALLBACK_MESSAGES_FILE;
  return MESSAGES_FILE; // default for writes
}

// ── Init: load from disk + Redis ─────────────────────────────────────────────
async function _doInit(): Promise<void> {
  const s = getState();
  // Try Redis first (most up-to-date, shared across workers)
  let loadedFromRedis = false;
  try {
    const redisData = await redisGet<Record<string, unknown>[]>(REDIS_MARKERS_KEY);
    if (redisData && Array.isArray(redisData) && redisData.length > 0) {
      s.messages = redisData;
      const ver = await getRedis().get(REDIS_VERSION_KEY);
      s.lastVersion = ver ? parseInt(ver, 10) : 0;
      loadedFromRedis = true;
      console.log(`[STORE] Loaded ${s.messages.length} markers from Redis (pid=${MY_PID})`);
    }
  } catch (err) {
    console.warn('[STORE] Redis load failed, falling back to disk:', err);
  }

  // Fallback to disk if Redis is empty
  if (!loadedFromRedis) {
    const filePath = resolveFilePath();
    try {
      const raw = await fsp.readFile(filePath, 'utf-8');
      const data = JSON.parse(raw);
      s.messages = Array.isArray(data) ? data : [];
      console.log(`[STORE] Loaded ${s.messages.length} markers from ${filePath} (pid=${MY_PID})`);

      // Seed Redis with disk data so other workers can read it
      if (s.messages.length > 0 && !isRedisDisabledInThisProcess()) {
        await writeToRedis();
      }
    } catch {
      s.messages = [];
      console.log(`[STORE] No existing data, starting empty (pid=${MY_PID})`);
    }
  }

  // Prune old markers
  const beforePrune = s.messages.length;
  s.messages = pruneMessages(s.messages);
  const pruned = beforePrune - s.messages.length;
  if (pruned > 0) {
    console.log(`[STORE] Pruned ${pruned} old markers (${s.messages.length} remaining)`);
    await writeToRedis();
  }

  s.initialized = true;
}

/**
 * Ensure the store is initialized. Safe to call multiple times.
 */
export async function initStore(): Promise<void> {
  const s = getState();
  if (s.initialized) return;
  if (!s.initPromise) {
    s.initPromise = _doInit();
  }
  await s.initPromise;
}

/**
 * Start polling Redis for marker updates from other workers.
 * Call once per process. Works across both instrumentation and API route contexts.
 */
export function startMarkerSync(): void {
  const s = getState();
  if (s.pollTimer) return;
  if (isRedisDisabledInThisProcess()) {
    console.log('[STORE] Marker Redis sync skipped (build or SKIP_REDIS=1)');
    return;
  }

  s.pollTimer = setInterval(async () => {
    try {
      const ver = await getRedis().get(REDIS_VERSION_KEY);
      const currentVersion = ver ? parseInt(ver, 10) : 0;
      if (currentVersion === s.lastVersion) return; // no changes

      const redisData = await redisGet<Record<string, unknown>[]>(REDIS_MARKERS_KEY);
      if (!redisData || !Array.isArray(redisData)) return;

      s.messages = redisData;
      s.lastVersion = currentVersion;
      s.lastIngestTime = Date.now();
      // Writer already published invalidation; only clear local HTTP cache for this process.
      clearMarkerDerivedApiCachesLocal();
    } catch {
      // Redis unavailable — keep using local data
    }
  }, POLL_INTERVAL);

  console.log(`[STORE] Redis polling started every ${POLL_INTERVAL}ms (pid=${MY_PID})`);

  // Start the position ticker alongside Redis polling
  startPositionTicker();
}

// ── Read: zero I/O ───────────────────────────────────────────────────────────

/** Get raw messages array (in-memory, no file I/O). */
export function getRawMessages(): Record<string, unknown>[] {
  return getState().messages;
}

/** Epoch ms of the last addMarker() call (0 = no ingests since boot). */
export function getLastIngestTime(): number {
  return getState().lastIngestTime;
}

/** Monotonic Redis-backed version — bumps on every persisted write; useful for clients / debugging. */
export function getMarkersVersion(): number {
  return getState().lastVersion;
}

/** Start a batch ingest: `addMarker` / `upsertByTrackId` update memory only until `endMarkerIngestBatch`. */
export function beginMarkerIngestBatch(): void {
  _markerPersistDeferDepth += 1;
}

/** End batch: single Redis + disk write + cache invalidation. Safe in `finally`. */
export async function endMarkerIngestBatch(): Promise<void> {
  _markerPersistDeferDepth = Math.max(0, _markerPersistDeferDepth - 1);
  if (_markerPersistDeferDepth > 0) return;
  await withWriteLock(async () => {
    await writeToRedisCore();
    await persistToDiskCore();
  });
}

export type MarkerIngestOptions = {
  /** When false, skip SSE (bulk / queue replay). Default true. */
  broadcast?: boolean;
};

// ── Write: mutate in-memory + Redis + disk ───────────────────────────────────

/** Add a marker to the store. Persists to Redis + disk.
 *  Spatial Correlator: before creating a new marker, check if a nearby
 *  marker of the same type group already exists and merge into it. */
export async function addMarker(
  marker: Record<string, unknown>,
  options?: MarkerIngestOptions,
): Promise<{ total: number; removed: number; id?: string }> {
  const doBroadcast = options?.broadcast !== false;
  return withWriteLock(async () => {
    const s = getState();

    // Spatial Correlator: try to merge into an existing nearby marker
    const matchIdx = findSpatialMatch(s.messages, marker);
    let resolvedId: string | undefined;
    if (matchIdx >= 0) {
      const existing = s.messages[matchIdx];
      mergeIntoExisting(existing, marker);
      resolvedId = existing.id as string | undefined;
      // Broadcast as track_update so client moves the marker
      if (doBroadcast) {
        const minConfSp = loadSettings().minConfidence ?? 0.65;
        if (ingestShouldBroadcastMarker(existing as Record<string, unknown>, minConfSp)) {
          const wireMarker: Record<string, unknown> = { ...existing };
          attachDisplayPolicyToPayload(existing as Record<string, unknown>, wireMarker);
          broadcastSSE({
            type: 'track_update',
            data: {
              track_id: existing.track_id || existing.id,
              mode: 'updated',
              marker: wireMarker,
            },
          });
        }
      }
    } else {
      s.messages.push(marker);
      applyDualChannelCorroborationGate(marker, marker);
      resolvedId = marker.id as string | undefined;
    }

    s.lastIngestTime = Date.now();
    const before = s.messages.length;
    s.messages = pruneMessages(s.messages);
    const removed = before - s.messages.length;

    await Promise.all([writeToRedis(), persistToDisk()]);
    invalidateDerivedCachesIfDeferred();

    return { total: s.messages.length, removed, id: resolvedId };
  });
}

/** Patch fields on an existing marker by ID. */
export async function patchMarker(id: string, updates: Record<string, unknown>): Promise<boolean> {
  return withWriteLock(async () => {
    const s = getState();
    const idx = s.messages.findIndex((m) => m.id === id);
    if (idx === -1) return false;

    const ALLOWED_FIELDS = [
      'trajectory', 'trajectory_source', 'prediction_confidence',
      'speed_kmh', 'computed_speed_kmh', 'distance_km', 'course_bearing', 'course_direction',
      'count', 'flight_phase', 'origin',
      'confidence', 'resolve_status', 'candidates', 'marker_icon',
      // Chain tracker: allow position/location updates for follow-up messages
      'lat', 'lng', 'location', 'place', 'region', 'text',
      // Track fields
      'track_id', 'positions', 'observations', 'observation_count',
      'ticker_bearing', 'is_estimated',
    ];

    for (const key of ALLOWED_FIELDS) {
      if (key in updates) {
        s.messages[idx][key] = updates[key];
      }
    }

    s.messages[idx].ts = new Date().toISOString();
    s.messages[idx].date = s.messages[idx].ts;

    applyDualChannelCorroborationGate(s.messages[idx], updates);

    await Promise.all([writeToRedis(), persistToDisk()]);
    invalidateDerivedCachesIfDeferred();

    return true;
  });
}

/**
 * Upsert a marker by track_id.
 * If a marker with the same track_id exists: update position, append to observations[],
 * increment observation_count, update trajectory and other fields.
 * If not found: add as new marker with initial observations + positions entry.
 * Returns { mode: 'created' | 'updated', id: string, total: number }
 *
 * Architecture: observations[] is PRISTINE — only real channel data goes here.
 * positions[] is the full trail (observations + ticker projections).
 * Speed is computed from observations[] only (no ticker noise).
 */
export async function upsertByTrackId(
  trackId: string,
  marker: Record<string, unknown>,
): Promise<{ mode: 'created' | 'updated'; id: string; total: number }> {
  return withWriteLock(async () => {
    const s = getState();
    const idx = s.messages.findIndex((m) => m.track_id === trackId);

    if (idx === -1) {
      // No exact track_id match — try Spatial Correlator before creating new marker
      const spatialIdx = findSpatialMatch(s.messages, marker);
      if (spatialIdx >= 0) {
        // Found a nearby marker of the same type — merge into it
        const existing = s.messages[spatialIdx];
        // Adopt the new track_id if the existing marker doesn't have one
        if (!existing.track_id) {
          existing.track_id = trackId;
        }
        mergeIntoExisting(existing, marker);
        s.lastIngestTime = Date.now();
        await Promise.all([writeToRedis(), persistToDisk()]);
        invalidateDerivedCachesIfDeferred();
        return { mode: 'updated' as const, id: existing.id as string, total: s.messages.length };
      }

      // No spatial match — create new marker with initial observation + position
      const now = Date.now();
      const entry = {
        lat: marker.lat,
        lng: marker.lng,
        ts: marker.created_at_epoch || now,
        source: marker.channel_name || 'unknown',
        channel_priority: coerceChannelPriority(marker.channel_priority),
      };
      marker.track_id = trackId;
      marker.observations = [entry];
      marker.positions = [entry];
      marker.observation_count = 1;
      applyDualChannelCorroborationGate(marker, marker);

      s.messages.push(marker);
      s.lastIngestTime = now;
      const before = s.messages.length;
      s.messages = pruneMessages(s.messages);

      await Promise.all([writeToRedis(), persistToDisk()]);
      invalidateDerivedCachesIfDeferred();

      return { mode: 'created' as const, id: marker.id as string, total: s.messages.length };
    }

    // Existing track — update with new observation
    const existing = s.messages[idx];
    const prevLat = existing.lat as number;
    const prevLng = existing.lng as number;
    const newLat = marker.lat as number;
    const newLng = marker.lng as number;

    // ── Anti-teleport: dynamic threshold based on speed × time gap ──
    // Use actual time since last observation to compute max plausible distance.
    const observations = (existing.observations as Array<Record<string, unknown>>) || [];
    const rawLastTs = observations.length > 0
      ? (observations[observations.length - 1].ts as number) || 0
      : (existing.created_at_epoch as number) || 0;
    const now = Date.now();
    const lastObsTs = normalizeObsEpochMs(rawLastTs, now);
    /** Ingest / worker clock skew buffer — observation older than last point ⇒ replay / reorder; don't mutate trail. */
    const newObsTs = normalizeObsEpochMs((marker.created_at_epoch as number) || 0, now);
    const staleObsReplay = observations.length > 0 && newObsTs + 12_000 < lastObsTs;
    if (staleObsReplay) {
      console.warn(
        `[STALE_OBS_SKIP] ${trackId} new ts ${newObsTs} << last ${lastObsTs} — merge text/light only`,
      );
    }
    const hoursSinceLastObs = Math.max((now - lastObsTs) / 3_600_000, 0.01);
    const currentSpeed = (existing.computed_speed_kmh as number) || (existing.speed_kmh as number) || 0;
    const ttype = (existing.threat_type as string) || '';
    const maxPlausibleSpeed = ['ballistic'].includes(ttype) ? 5000
      : ['missile', 'krylata', 'raketa'].includes(ttype) ? 1200
      : ['kab'].includes(ttype) ? 1000
      : ['avia'].includes(ttype) ? 900
      : 350; // UAV/drone/shahed/rozved
    const speedForCalc = currentSpeed > 0 ? Math.min(currentSpeed * 1.5, maxPlausibleSpeed) : maxPlausibleSpeed;
    const antiTeleportKm = Math.max(speedForCalc * hoursSinceLastObs * 1.5, 25);

    const jumpDist = haversineKm(prevLat, prevLng, newLat, newLng);
    const positionRejected = jumpDist > antiTeleportKm;
    if (positionRejected) {
      console.warn(
        `[TELEPORT_BLOCKED] ${trackId} jumped ${jumpDist.toFixed(0)}km (threshold=${antiTeleportKm.toFixed(0)}km) ` +
        `(${prevLat.toFixed(2)},${prevLng.toFixed(2)}) → (${newLat.toFixed(2)},${newLng.toFixed(2)}). ` +
        `Keeping map position + trail; merging text/count only (likely bad geocode).`,
      );
    }

    const prevConfU =
      typeof existing.confidence === 'number' && Number.isFinite(existing.confidence)
        ? existing.confidence
        : undefined;
    const incConfU =
      typeof marker.confidence === 'number' && Number.isFinite(marker.confidence)
        ? marker.confidence
        : undefined;
    /** Within physics window but likely wrong city / duplicate parse — don't drag the track. */
    const weakGeoHold =
      !positionRejected &&
      jumpDist >= 3.5 &&
      incConfU != null &&
      prevConfU != null &&
      incConfU < prevConfU - 0.15 &&
      incConfU < 0.42;
    if (weakGeoHold) {
      console.warn(
        `[WEAK_GEO_HOLD] ${trackId} jump=${jumpDist.toFixed(1)}km conf ${prevConfU.toFixed(2)}→${incConfU.toFixed(2)} — keeping position`,
      );
    }

    const skipPositionUpdate = positionRejected || weakGeoHold || staleObsReplay;

    if (!skipPositionUpdate) {
      // ── Append to observations[] (pristine channel data) ──
      const obsEntry = {
        lat: newLat,
        lng: newLng,
        ts: newObsTs,
        source: marker.channel_name || 'unknown',
        channel_priority: coerceChannelPriority(marker.channel_priority),
      };
      observations.push(obsEntry);
      if (observations.length > 30) {
        observations.splice(0, observations.length - 30);
      }
      existing.observations = observations;

      const positions = (existing.positions as Array<Record<string, unknown>>) || [];
      positions.push(obsEntry);
      if (positions.length > 50) {
        positions.splice(0, positions.length - 50);
      }
      existing.positions = positions;

      if (observations.length >= 2) {
        const prev = observations[observations.length - 2];
        const curr = observations[observations.length - 1];
        const prevTs = normalizeObsEpochMs((prev.ts as number) || 0, now);
        const currTs = normalizeObsEpochMs((curr.ts as number) || 0, now);
        const dtHours = (currTs - prevTs) / 3_600_000;
        if (dtHours > 0.001) {
          const distKm = haversineKm(
            prev.lat as number, prev.lng as number,
            curr.lat as number, curr.lng as number,
          );
          if (distKm > 1) {
            const rawSpeed = Math.round(distKm / dtHours);
            const minSpeed = 50;
            if (rawSpeed >= minSpeed && rawSpeed <= maxPlausibleSpeed) {
              const prevComputed = existing.computed_speed_kmh as number | undefined;
              if (prevComputed && prevComputed > 0) {
                const alpha = 0.4;
                existing.computed_speed_kmh = Math.round((alpha * rawSpeed) + ((1 - alpha) * prevComputed));
              } else {
                existing.computed_speed_kmh = rawSpeed;
              }
            }
          }
        }
      }

      existing.observation_count = ((existing.observation_count as number) || 1) + 1;

      const UPDATE_FIELDS = [
        'lat', 'lng', 'location', 'place', 'region', 'text',
        'trajectory', 'trajectory_source', 'prediction_confidence',
        'course_bearing', 'course_direction', 'speed_kmh', 'distance_km',
        'flight_phase', 'origin', 'count', 'ticker_bearing', 'is_estimated',
        'confidence', 'confidence_0_100', 'placement_mode', 'resolve_status',
        'candidates', 'marker_icon',
      ];
      for (const key of UPDATE_FIELDS) {
        if (key in marker && marker[key] != null) {
          if (key === 'text' && typeof marker.text === 'string') {
            existing.text = mergeThreatSourceText(
              (existing.text as string) || '',
              marker.text,
            );
          } else {
            existing[key] = marker[key];
          }
        }
      }

      if (existing.computed_speed_kmh && (existing.computed_speed_kmh as number) > 0) {
        existing.speed_kmh = existing.computed_speed_kmh;
      }
    } else {
      if (typeof marker.text === 'string' && marker.text.trim()) {
        existing.text = mergeThreatSourceText(
          (existing.text as string) || '',
          marker.text,
        );
      }
      const newCount = Number(marker.count);
      if (!Number.isNaN(newCount) && newCount > 0) {
        const prevC = Number(existing.count);
        existing.count = Math.max(Number.isNaN(prevC) ? 1 : prevC, newCount);
      }
      appendCorroborationObservationOnly(existing, prevLat, prevLng, newObsTs, marker);
      if (weakGeoHold || staleObsReplay) {
        const LIGHT = [
          'course_bearing', 'course_direction', 'ticker_bearing',
          'flight_phase', 'place', 'region', 'resolve_status', 'marker_icon',
          'placement_mode', 'confidence_0_100', 'confidence', 'trajectory',
          'trajectory_source', 'prediction_confidence',
        ] as const;
        for (const key of LIGHT) {
          if (key in marker && marker[key] != null) {
            existing[key] = marker[key];
          }
        }
      }
    }

    // Preserve original creation time — NEVER overwrite.
    // created_at_epoch stays at original value for pruning reference.
    if (!existing.created_at_epoch && marker.created_at_epoch) {
      existing.created_at_epoch = marker.created_at_epoch;
    }

    // Last ingest / ticker touch (sorting, prune fallback). Map TTL uses last
    // `observations[].ts` when present (see `parseMessageTime` in build-markers).
    existing.last_update_epoch = now;

    existing.ts = new Date().toISOString();
    existing.date = existing.ts;
    s.lastIngestTime = now;

    applyDualChannelCorroborationGate(existing, marker);

    await Promise.all([writeToRedis(), persistToDisk()]);
    invalidateDerivedCachesIfDeferred();

    return { mode: 'updated' as const, id: existing.id as string, total: s.messages.length };
  });
}

// ── Spatial Correlator ────────────────────────────────────────────────────────
// Before creating a new marker, check if a nearby marker of the same threat group
// already exists. If so, update that marker instead of creating a duplicate.
// This prevents 7 markers for 1 drone when multiple channels report the same target.

/** Normalize observation epoch to ms (worker may send seconds). */
function normalizeObsEpochMs(ts: number, fallbackMs: number): number {
  if (!Number.isFinite(ts) || ts <= 0) return fallbackMs;
  return ts > 10_000_000_000 ? Math.round(ts) : Math.round(ts * 1000);
}

function coerceChannelPriority(v: unknown): number {
  const n = typeof v === 'number' ? v : Number(v);
  if (Number.isFinite(n)) return n;
  return 99;
}

/**
 * Public map / SSE: require corroboration from a second distinct channel_name in observations,
 * unless any observation used channel_priority <= 1 (official sources). See worker channel_priority.
 * Phantom avia (`resolve_status` phantom_avia) always uses this gate, even when dualSourceMapGate is off.
 */
function applyDualChannelCorroborationGate(
  record: Record<string, unknown>,
  marker?: Record<string, unknown>,
): void {
  if (record.manual === true) {
    record.corroboration_pending = false;
    return;
  }
  if (marker && typeof marker.hidden === 'boolean') {
    record.hidden_reason_worker = marker.hidden;
  }

  let dualGate = false;
  try {
    dualGate = loadSettings().dualSourceMapGate === true;
  } catch {
    dualGate = false;
  }
  const requireCorroboration = dualGate || recordHasPhantomAvia(record, marker);
  if (!requireCorroboration) {
    record.corroboration_pending = false;
    record.hidden = record.hidden_reason_worker === true;
    return;
  }

  const obsRaw = record.observations as Array<Record<string, unknown>> | undefined;
  let obs: Array<Record<string, unknown>>;
  if (obsRaw && obsRaw.length > 0) {
    obs = obsRaw;
  } else {
    const ch = record.channel_name;
    if (typeof ch === 'string' && ch.trim()) {
      obs = [{ source: ch, channel_priority: record.channel_priority }];
    } else {
      obs = [];
    }
  }

  const hasPriority1 = obs.some((o) => coerceChannelPriority(o.channel_priority) <= 1);
  const distinctSources = new Set(
    obs.map((o) => (typeof o.source === 'string' ? o.source.trim() : '')).filter(Boolean),
  );
  const pending = !hasPriority1 && distinctSources.size < 2;
  record.corroboration_pending = pending;
  const workerH = record.hidden_reason_worker === true;
  record.hidden = workerH || pending;
}

/** When position merge is skipped, still record the reporting channel for corroboration counting. */
function appendCorroborationObservationOnly(
  existing: Record<string, unknown>,
  lat: number,
  lng: number,
  ts: number,
  marker: Record<string, unknown>,
): void {
  const src = ((marker.channel_name as string) || '').trim() || 'unknown';
  const observations = (existing.observations as Array<Record<string, unknown>>) || [];
  if (observations.length > 0) {
    const lastSrc = String((observations[observations.length - 1].source as string) || '').trim();
    if (lastSrc === src) return;
  }
  const obsEntry: Record<string, unknown> = {
    lat,
    lng,
    ts,
    source: src,
    channel_priority: coerceChannelPriority(marker.channel_priority),
  };
  observations.push(obsEntry);
  if (observations.length > 30) observations.splice(0, observations.length - 30);
  existing.observations = observations;
  existing.observation_count = ((existing.observation_count as number) || 1) + 1;
}

function extractCorrelatorBearing(m: Record<string, unknown>): number | null {
  const cb = m.course_bearing as number | undefined;
  if (typeof cb === 'number' && Number.isFinite(cb)) return cb;
  const tb = m.ticker_bearing as number | undefined;
  if (typeof tb === 'number' && Number.isFinite(tb)) return tb;
  return null;
}

/** Normalize place/location for same-settlement dedupe (spatial correlator). */
function correlatorPlaceFingerprint(marker: Record<string, unknown>): string | null {
  const raw = (marker.place || marker.location || marker.city || '').toString().trim().toLowerCase();
  if (raw.length < 2) return null;
  return raw.replace(/\s+/g, ' ');
}

/** Map individual threat types to correlation groups */
const CORRELATION_GROUP: Record<string, string> = {
  shahed: 'uav', drone: 'uav', uav: 'uav', fpv: 'uav', rozved: 'uav',
  raketa: 'missile', missile: 'missile', pusk: 'missile', launch: 'missile', ballistic: 'missile',
  kab: 'guided', rszv: 'guided',
  avia: 'avia',
};

/** Max age (ms) for a marker to be eligible for spatial correlation */
const SPATIAL_MATCH_MAX_AGE_MS = 15 * 60 * 1000; // 15 minutes
/** Max distance (km) for spatial correlation */
const SPATIAL_MATCH_RADIUS_KM = 10;
/** Wider gate when both reports lack bearing (common for text-only channels). */
const SPATIAL_MATCH_RADIUS_KM_NO_BEARING_UAV = 18;
/** Max bearing difference (degrees) for spatial correlation. Ignored if either marker has no bearing. */
const SPATIAL_MATCH_BEARING_TOLERANCE = 60;

/** Same-text dedup must never merge events hundreds of km apart (templates / reposts). */
const SPATIAL_SAME_TEXT_MAX_KM = 32;
/** Same-channel short-window merge — still bounded so east/west events do not fuse. */
const SPATIAL_SAME_CHANNEL_MAX_KM = 30;
const SPATIAL_TIME_WINDOW_UAV_KM = 24;
const SPATIAL_TIME_WINDOW_UAV_BEARING_KM = 38;
const SPATIAL_TIME_WINDOW_FAST_KM = 42;
const SPATIAL_TIME_WINDOW_FAST_BEARING_KM = 88;

/**
 * When both markers carry a stable regional key from the worker (`resolved_oblast_hasc`,
 * `region_key`, or `oblast_id`), refuse cross-oblast spatial merges — different regions
 * are different events even if timing/text look related.
 */
function extractCorrelationRegionKey(marker: Record<string, unknown>): string | null {
  const h = marker.resolved_oblast_hasc;
  if (typeof h === 'string' && h.trim()) {
    return `hasc:${h.trim().toUpperCase()}`;
  }
  const rk = marker.region_key;
  if (typeof rk === 'string' && rk.trim()) {
    return `rk:${rk.trim().toLowerCase()}`;
  }
  const oid = marker.oblast_id;
  if (typeof oid === 'string' && oid.trim()) return `id:${oid.trim().toLowerCase()}`;
  if (typeof oid === 'number' && Number.isFinite(oid)) return `id:${oid}`;
  return null;
}

/**
 * Find the nearest existing marker of the same threat-type group within
 * SPATIAL_MATCH_RADIUS_KM and with compatible bearing (±60°).
 * Returns the index in `messages[]` or -1 if no match.
 */
function findSpatialMatch(
  messages: Record<string, unknown>[],
  newMarker: Record<string, unknown>,
): number {
  try {
    if (loadSettings().spatialCorrelatorEnabled === false) return -1;
  } catch {
    /* keep correlator on */
  }

  const newLat = newMarker.lat as number;
  const newLng = newMarker.lng as number;
  if (newLat == null || newLng == null) return -1;

  const newType = (newMarker.threat_type as string) || '';
  const newGroup = CORRELATION_GROUP[newType];
  if (!newGroup) return -1; // static types (explosion, alarm, etc.) — don't merge

  const newBearing = extractCorrelatorBearing(newMarker);
  const now = Date.now();

  let bestIdx = -1;
  let bestDist = Infinity;

  for (let i = 0; i < messages.length; i++) {
    const m = messages[i];
    const mType = (m.threat_type as string) || '';
    const mGroup = CORRELATION_GROUP[mType];
    if (mGroup !== newGroup) continue;

    const rkNew = extractCorrelationRegionKey(newMarker);
    const rkExist = extractCorrelationRegionKey(m);
    if (rkNew !== null && rkExist !== null && rkNew !== rkExist) {
      continue;
    }

    // Check age: must have been updated recently
    const updateEpoch = m.last_update_epoch as number | undefined;
    const createdEpoch = m.created_at_epoch as number | undefined;
    const mTsFallback = m.ts ? new Date(m.ts as string).getTime() : 0;
    const mTs = updateEpoch && updateEpoch > 1000000000
      ? (updateEpoch > 10000000000 ? updateEpoch : updateEpoch * 1000)
      : createdEpoch && createdEpoch > 1000000000
        ? (createdEpoch > 10000000000 ? createdEpoch : createdEpoch * 1000)
        : mTsFallback > 0 ? mTsFallback : 0;
        
    if (mTs > 0 && (now - mTs) > SPATIAL_MATCH_MAX_AGE_MS) continue;

    const mLat = m.lat as number;
    const mLng = m.lng as number;
    if (mLat == null || mLng == null) continue;

    const dist = haversineKm(newLat, newLng, mLat, mLng);
    const mBearing = extractCorrelatorBearing(m);
    const bothLackBearing = newBearing == null && mBearing == null;

    let bearingsCompatible = false;
    if (newBearing != null && mBearing != null) {
      let diff = Math.abs(newBearing - mBearing) % 360;
      if (diff > 180) diff = 360 - diff;
      bearingsCompatible = diff <= SPATIAL_MATCH_BEARING_TOLERANCE;
    }

    // --- Dynamic Spatial Expansion (bounded; wide merges caused east/west false joins) ---
    const timeDiffMins = mTs > 0 ? Math.abs(now - mTs) / 60000 : Infinity;
    let maxDist = SPATIAL_MATCH_RADIUS_KM;

    const mText = (m.text as string || '').toLowerCase().trim();
    const newText = (newMarker.text as string || '').toLowerCase().trim();
    const mChannel = m.channel_name as string || '';
    const newChannel = newMarker.channel_name as string || '';

    if (mText && newText && mText === newText) {
      maxDist = bearingsCompatible ? 40 : SPATIAL_SAME_TEXT_MAX_KM;
    } else if (mChannel && newChannel && mChannel === newChannel && timeDiffMins <= 3) {
      maxDist = bearingsCompatible ? 42 : SPATIAL_SAME_CHANNEL_MAX_KM;
    } else if (timeDiffMins <= 4) {
      if (newGroup === 'uav') {
        maxDist = bearingsCompatible
          ? SPATIAL_TIME_WINDOW_UAV_BEARING_KM
          : SPATIAL_TIME_WINDOW_UAV_KM;
      } else if (newGroup === 'missile' || newGroup === 'avia' || newGroup === 'guided') {
        maxDist = bearingsCompatible
          ? SPATIAL_TIME_WINDOW_FAST_BEARING_KM
          : SPATIAL_TIME_WINDOW_FAST_KM;
      }
    } else {
      if (newGroup === 'uav' && bothLackBearing) {
        maxDist = SPATIAL_MATCH_RADIUS_KM_NO_BEARING_UAV;
      }
    }

    // Same settlement label + same regional key → allow slightly wider merge (multi-channel duplicates).
    const fpNew = correlatorPlaceFingerprint(newMarker);
    const fpM = correlatorPlaceFingerprint(m);
    if (
      fpNew &&
      fpM &&
      fpNew === fpM &&
      rkNew !== null &&
      rkExist !== null &&
      rkNew === rkExist
    ) {
      maxDist = Math.max(maxDist, Math.min(26, maxDist + 10));
    }

    if (dist > maxDist) continue;

    // Bearing check: if both markers have bearing (course or ticker), they must be within ±60°
    if (newBearing != null && mBearing != null) {
      let diff = Math.abs(newBearing - mBearing) % 360;
      if (diff > 180) diff = 360 - diff;
      if (diff > SPATIAL_MATCH_BEARING_TOLERANCE) continue;
    }

    // Prefer closest match
    if (dist < bestDist) {
      bestDist = dist;
      bestIdx = i;
    }
  }

  return bestIdx;
}

/** Cap merged raw Telegram sources so Redis/payload stays bounded */
const MAX_MERGED_SOURCE_TEXT = 4000;
const SOURCE_TEXT_SEP = '\n---\n';

/**
 * Combine messages from multiple channels / updates on one track.
 * Keeps distinct wording instead of last-write-wins.
 */
function mergeThreatSourceText(prev: string, incoming: string): string {
  const a = (prev || '').trim();
  const b = (incoming || '').trim();
  if (!b) return a;
  if (!a) return b;
  if (a === b) return a;
  const aLow = a.toLowerCase();
  const bLow = b.toLowerCase();
  if (aLow.includes(bLow)) return a;
  if (bLow.includes(aLow)) return b;
  const merged = `${a}${SOURCE_TEXT_SEP}${b}`;
  if (merged.length <= MAX_MERGED_SOURCE_TEXT) return merged;
  return `…${merged.slice(-(MAX_MERGED_SOURCE_TEXT - 1))}`;
}

/**
 * Merge a new marker into an existing spatial match.
 * Updates position, appends observation, refreshes timestamps.
 */
function mergeIntoExisting(
  existing: Record<string, unknown>,
  newMarker: Record<string, unknown>,
): void {
  const now = Date.now();
  const newLat = newMarker.lat as number;
  const newLng = newMarker.lng as number;
  const oldLat = existing.lat as number;
  const oldLng = existing.lng as number;

  const jumpKm =
    Number.isFinite(oldLat) && Number.isFinite(oldLng)
      ? haversineKm(oldLat, oldLng, newLat, newLng)
      : 0;
  
  const prevConf = typeof existing.confidence === 'number' && Number.isFinite(existing.confidence)
      ? existing.confidence : 0;
  const incConf = typeof newMarker.confidence === 'number' && Number.isFinite(newMarker.confidence)
      ? newMarker.confidence : 0;

  // --- SWARM / PINBALL PREVENTION ---
  // If cross-channel reports have different coordinates for the same drone (dist >= 5km),
  // we ONLY move the physical marker if the new report is STRICTLY MORE accurate (higher confidence).
  // Otherwise, we keep the marker where it is and safely suck up the text/counts without "teleporting" the pin.
  const rejectPositionOnly = jumpKm >= 5 && incConf <= prevConf;

  const observationsPre = (existing.observations as Array<Record<string, unknown>>) || [];
  const rawLastTsMerge = observationsPre.length > 0
    ? (observationsPre[observationsPre.length - 1].ts as number) || 0
    : (existing.created_at_epoch as number) || 0;
  const lastObsTsMerge = normalizeObsEpochMs(rawLastTsMerge, now);
  const newTsMerge = normalizeObsEpochMs((newMarker.created_at_epoch as number) || 0, now);
  const staleSpatial = observationsPre.length > 0 && newTsMerge + 12_000 < lastObsTsMerge;
  if (staleSpatial) {
    console.warn(
      `[STALE_OBS_SKIP] spatial merge into ${existing.id}: ts ${newTsMerge} << last ${lastObsTsMerge} — text/light only`,
    );
    existing.last_update_epoch = now;
    const newCountSt = Number(newMarker.count);
    if (!Number.isNaN(newCountSt) && newCountSt > 0) {
      const prev = Number(existing.count);
      existing.count = Math.max(Number.isNaN(prev) ? 1 : prev, newCountSt);
    }
    if (typeof newMarker.text === 'string' && newMarker.text.trim()) {
      existing.text = mergeThreatSourceText(
        (existing.text as string) || '',
        newMarker.text,
      );
    }
    const MERGE_STALE_LIGHT = [
      'course_bearing', 'course_direction', 'ticker_bearing',
      'speed_kmh', 'distance_km', 'flight_phase', 'place', 'region',
      'resolve_status', 'marker_icon', 'placement_mode', 'confidence_0_100',
      'trajectory', 'trajectory_source', 'prediction_confidence',
    ] as const;
    for (const key of MERGE_STALE_LIGHT) {
      if (key in newMarker && newMarker[key] != null) {
        existing[key] = newMarker[key];
      }
    }
    appendCorroborationObservationOnly(existing, oldLat, oldLng, newTsMerge, newMarker);
    applyDualChannelCorroborationGate(existing, newMarker);
    return;
  }

  if (rejectPositionOnly) {
    console.warn(
      `[SPATIAL_MERGE_TEXT_ONLY] jump=${jumpKm.toFixed(1)}km conf ${prevConf?.toFixed(2)}→${incConf?.toFixed(2)} — keeping position, merging text`,
    );
    existing.last_update_epoch = now;
    const newCount = Number(newMarker.count);
    if (!Number.isNaN(newCount) && newCount > 0) {
      const prev = Number(existing.count);
      existing.count = Math.max(Number.isNaN(prev) ? 1 : prev, newCount);
    }
    if (typeof newMarker.text === 'string' && newMarker.text.trim()) {
      existing.text = mergeThreatSourceText(
        (existing.text as string) || '',
        newMarker.text,
      );
    }
    const MERGE_FIELDS_LIGHT = [
      'course_bearing', 'course_direction', 'ticker_bearing',
      'speed_kmh', 'distance_km', 'flight_phase', 'place', 'region',
      'resolve_status', 'marker_icon', 'placement_mode', 'confidence_0_100',
      'trajectory', 'trajectory_source', 'prediction_confidence',
    ] as const;
    for (const key of MERGE_FIELDS_LIGHT) {
      if (key in newMarker && newMarker[key] != null) {
        existing[key] = newMarker[key];
      }
    }
    appendCorroborationObservationOnly(existing, oldLat, oldLng, newTsMerge, newMarker);
    applyDualChannelCorroborationGate(existing, newMarker);
    return;
  }

  // Update position
  existing.lat = newLat;
  existing.lng = newLng;

  // Append observation
  const obsEntry = {
    lat: newLat,
    lng: newLng,
    ts: newTsMerge,
    source: (newMarker.channel_name as string) || 'spatial_match',
    channel_priority: coerceChannelPriority(newMarker.channel_priority),
  };
  const observations = (existing.observations as Array<Record<string, unknown>>) || [];
  observations.push(obsEntry);
  if (observations.length > 30) observations.splice(0, observations.length - 30);
  existing.observations = observations;

  // Append to positions[]
  const positions = (existing.positions as Array<Record<string, unknown>>) || [];
  positions.push(obsEntry);
  if (positions.length > 50) positions.splice(0, positions.length - 50);
  existing.positions = positions;

  existing.observation_count = ((existing.observation_count as number) || 1) + 1;

  const newCount = Number(newMarker.count);
  if (!Number.isNaN(newCount) && newCount > 0) {
    const prev = Number(existing.count);
    existing.count = Math.max(Number.isNaN(prev) ? 1 : prev, newCount);
  }

  const newConf = newMarker.confidence;
  if (typeof newConf === 'number' && !Number.isNaN(newConf)) {
    const prevC = existing.confidence as number | undefined;
    if (typeof prevC !== 'number' || newConf > prevC) {
      existing.confidence = newConf;
    }
  }

  const newC100 = newMarker.confidence_0_100;
  if (typeof newC100 === 'number' && Number.isFinite(newC100)) {
    const prev100 = existing.confidence_0_100 as number | undefined;
    if (typeof prev100 !== 'number' || newC100 > prev100) {
      existing.confidence_0_100 = newC100;
    }
  }

  // Update fields from the new marker (if present)
  const MERGE_FIELDS = [
    'course_bearing', 'course_direction', 'trajectory', 'trajectory_source',
    'prediction_confidence', 'speed_kmh', 'distance_km', 'flight_phase',
    'place', 'region', 'ticker_bearing', 'is_estimated',
    'resolve_status', 'candidates', 'marker_icon', 'placement_mode',
  ];
  for (const key of MERGE_FIELDS) {
    if (key in newMarker && newMarker[key] != null) {
      existing[key] = newMarker[key];
    }
  }

  if (typeof newMarker.text === 'string' && newMarker.text.trim()) {
    existing.text = mergeThreatSourceText(
      (existing.text as string) || '',
      newMarker.text,
    );
  }

  existing.last_update_epoch = now;
  existing.ts = new Date(now).toISOString();
  existing.date = existing.ts;

  console.log(
    `[SPATIAL_MATCH] Merged into ${existing.id} (track=${existing.track_id || 'none'}) ` +
    `← new ${newMarker.threat_type} at (${newLat.toFixed(2)},${newLng.toFixed(2)}) ` +
    `from ${newMarker.channel_name || 'unknown'}`
  );

  applyDualChannelCorroborationGate(existing, newMarker);
}

// ── Geo helpers ──────────────────────────────────────────────────────────────
function haversineKm(lat1: number, lng1: number, lat2: number, lng2: number): number {
  const R = 6371;
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLng = (lng2 - lng1) * Math.PI / 180;
  const a = Math.sin(dLat / 2) ** 2 +
    Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
    Math.sin(dLng / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

/**
 * Move a point along a given bearing by a given distance.
 * Returns new [lat, lng].
 */
function destinationPoint(lat: number, lng: number, bearingDeg: number, distKm: number): [number, number] {
  const R = 6371;
  const toRad = Math.PI / 180;
  const lat1 = lat * toRad;
  const lng1 = lng * toRad;
  const brg = bearingDeg * toRad;
  const d = distKm / R; // angular distance

  const lat2 = Math.asin(
    Math.sin(lat1) * Math.cos(d) +
    Math.cos(lat1) * Math.sin(d) * Math.cos(brg)
  );
  const lng2 = lng1 + Math.atan2(
    Math.sin(brg) * Math.sin(d) * Math.cos(lat1),
    Math.cos(d) - Math.sin(lat1) * Math.sin(lat2)
  );

  return [lat2 / toRad, lng2 / toRad];
}

// ── Position Ticker ──────────────────────────────────────────────────────────
// Advances moving markers every TICK_INTERVAL_MS based on their speed + bearing.
// This ensures markers move on the server even when no browser is open.
// IMPORTANT: Ticker writes ONLY to positions[] — observations[] is pristine.

const TICK_INTERVAL_MS = 15_000; // 15s — moving markers tick (less CPU; slight delay vs 10s)
const TICKER_GLOBAL_KEY = '__neptun_position_ticker__';
const REDIS_TICKER_LOCK_KEY = 'ticker:lock'; // Redis lock — only one PM2 worker ticks at a time
const REDIS_TICKER_LOCK_TTL = 22; // seconds — must be > TICK_INTERVAL_MS / 1000

// Batch persist: write to Redis+disk every 30s (every 3rd tick), not every tick
const TICKER_PERSIST_INTERVAL = 30_000;
let _lastTickerPersistTime = 0;

/** Threat types that never move (static events). */
const STATIC_THREAT_TYPES = new Set([
  'explosion', 'vibuh', 'alert', 'allclear', 'chemical', 'nuclear',
  'artillery', 'obstril', 'info',
]);

/**
 * Start the server-side position ticker.
 * Every TICK_INTERVAL_MS, iterates all markers with speed + bearing
 * and advances their position. Broadcasts track_update SSE events.
 * Safe to call multiple times — only one ticker per process.
 */
export function startPositionTicker(): void {
  // Prevent duplicate tickers (globalThis-safe for PM2 + Next.js standalone)
  if ((globalThis as Record<string, unknown>)[TICKER_GLOBAL_KEY]) return;
  (globalThis as Record<string, unknown>)[TICKER_GLOBAL_KEY] = true;

  setInterval(() => {
    try {
      tickPositions();
    } catch (err) {
      console.warn('[TICKER] Error:', err);
    }
  }, TICK_INTERVAL_MS);

  console.log(`[TICKER] Position ticker started — ${TICK_INTERVAL_MS}ms interval (pid=${MY_PID})`);
}

function tickPositions(): void {
  // Acquire Redis lock so only one PM2 worker ticks per interval.
  // SET NX EX = atomic "set if not exists" with TTL — perfect for distributed locks.
  getRedis().set(REDIS_TICKER_LOCK_KEY, String(MY_PID), 'EX', REDIS_TICKER_LOCK_TTL, 'NX')
    .then((acquired) => {
      if (!acquired) return; // another worker holds the lock
      doTickPositions();
    })
    .catch((err) => console.warn('[TICKER] lock error:', err));
}

function doTickPositions(): void {
  const s = getState();
  if (s.messages.length === 0) return;

  const now = Date.now();
  let dirty = false;
  const batchUpdates: { track_id: string; mode: string; marker: Record<string, unknown> }[] = [];

  for (const m of s.messages) {
    const threatType = (m.threat_type as string) || '';
    if (STATIC_THREAT_TYPES.has(threatType)) continue;
    if (m.manual) continue;

    const obs = m.observations as Array<{ts: number}> | undefined;
    const lastRealTs = obs && obs.length > 0 ? obs[obs.length - 1].ts : m.created_at_epoch as number;
    if (lastRealTs && (now - lastRealTs > 10 * 60 * 1000)) {
      continue;
    }

    const speed = (m.speed_kmh as number) || (m.computed_speed_kmh as number) || 0;
    let bearing = m.course_bearing as number | null | undefined;

    if (bearing == null) {
      bearing = (m as Record<string, unknown>).ticker_bearing as number | null | undefined;
    }
    if (bearing == null) {
      const trajFb = m.trajectory as { start?: number[]; end?: number[] } | undefined;
      if (trajFb?.start && trajFb?.end) {
        const dLat = trajFb.end[0] - trajFb.start[0];
        const midLat = (trajFb.start[0] + trajFb.end[0]) / 2;
        const cosLat = Math.cos(midLat * Math.PI / 180);
        const dLng = (trajFb.end[1] - trajFb.start[1]) * cosLat;
        if (Math.abs(dLat) > 0.001 || Math.abs(dLng) > 0.001) {
          bearing = (Math.atan2(dLng, dLat) * (180 / Math.PI) + 360) % 360;
        }
      }
      if (bearing == null) {
        const obsFb = (m.observations as Array<{ lat: number; lng: number }>) ||
                       (m.positions as Array<{ lat: number; lng: number }>);
        if (obsFb && obsFb.length >= 2) {
          const prev = obsFb[obsFb.length - 2];
          const last = obsFb[obsFb.length - 1];
          const dLat2 = last.lat - prev.lat;
          const midLat2 = (prev.lat + last.lat) / 2;
          const cosLat2 = Math.cos(midLat2 * Math.PI / 180);
          const dLng2 = (last.lng - prev.lng) * cosLat2;
          if (Math.abs(dLat2) > 0.0001 || Math.abs(dLng2) > 0.0001) {
            bearing = (Math.atan2(dLng2, dLat2) * (180 / Math.PI) + 360) % 360;
          }
        }
      }
    }
    if (speed <= 0 || bearing == null) continue;

    const curLat = Number(m.lat);
    const curLng = Number(m.lng);
    if (!Number.isFinite(curLat) || !Number.isFinite(curLng)) continue;

    let positions = m.positions as Array<Record<string, unknown>> | undefined;
    if (!positions || positions.length === 0) {
      const obs = m.observations as Array<{ lat: number; lng: number; ts?: number }> | undefined;
      if (obs && obs.length >= 1) {
        positions = obs.map((o) => {
          const ts = typeof o.ts === 'number' && o.ts > 0
            ? (o.ts > 10_000_000_000 ? o.ts : Math.round(o.ts * 1000))
            : now;
          return {
            lat: Number(o.lat),
            lng: Number(o.lng),
            ts,
            source: 'obs',
          };
        });
      } else {
        positions = [{ lat: curLat, lng: curLng, ts: now, source: 'ticker_bootstrap' }];
      }
      m.positions = positions;
    }

    const traj = m.trajectory as { end?: [number, number] } | undefined;
    if (traj?.end) {
      const distToEnd = haversineKm(curLat, curLng, traj.end[0], traj.end[1]);
      if (distToEnd < 5) continue;
    }

    const dtHours = TICK_INTERVAL_MS / 3_600_000;
    const distKm = speed * dtHours;

    const [newLat, newLng] = destinationPoint(curLat, curLng, bearing, distKm);

    m.lat = newLat;
    m.lng = newLng;

    positions.push({
      lat: newLat,
      lng: newLng,
      ts: now,
      source: 'ticker',
    });
    if (positions.length > 50) {
      positions.splice(0, positions.length - 50);
    }
    m.positions = positions;

    m.ts = new Date(now).toISOString();
    m.date = m.ts;
    m.last_update_epoch = now;

    dirty = true;

    const tid = (m.track_id != null && String(m.track_id).length > 0)
      ? String(m.track_id)
      : String(m.id ?? '');
    if (!tid) continue;

    batchUpdates.push({
      track_id: tid,
      mode: 'updated',
      marker: {
        id: m.id,
        lat: newLat,
        lng: newLng,
        speed_kmh: speed,
        course_bearing: bearing,
        created_at_epoch: m.created_at_epoch,
        ts: now,
      },
    });
  }

  // Single batched SSE broadcast instead of per-marker (N broadcasts → 1).
  // Minimal deltas only — no display_* here (hot path); clients keep prior policy or refetch /api/data.
  if (batchUpdates.length > 0) {
    broadcastSSE({
      type: 'track_batch',
      data: { updates: batchUpdates },
    });
  }

  if (dirty) {
    s.lastIngestTime = now;
    if (now - _lastTickerPersistTime >= TICKER_PERSIST_INTERVAL) {
      _lastTickerPersistTime = now;
      withWriteLock(async () => {
        await Promise.all([writeToRedisCore(), persistToDiskCore()]);
      }).catch((err) => console.warn('[TICKER] persist error:', err));
    }
  }
}

/** Admin patch — allows any field update on a marker by ID. */
export async function adminPatchMarker(id: string, updates: Record<string, unknown>): Promise<boolean> {
  return withWriteLock(async () => {
    const s = getState();
    const idx = s.messages.findIndex((m) => m.id === id);
    if (idx === -1) return false;

    for (const [key, value] of Object.entries(updates)) {
      if (key !== 'id') {
        s.messages[idx][key] = value;
      }
    }

    s.messages[idx].ts = new Date().toISOString();
    s.messages[idx].date = s.messages[idx].ts;

    await Promise.all([writeToRedis(), persistToDisk()]);

    return true;
  });
}

/** Delete a marker by ID. */
export async function deleteMarker(id: string): Promise<boolean> {
  return withWriteLock(async () => {
    const s = getState();
    const before = s.messages.length;
    s.messages = s.messages.filter((m) => String(m.id) !== String(id) && String(m.track_id) !== String(id));
    if (s.messages.length === before) return false;

    await Promise.all([writeToRedis(), persistToDisk()]);

    // Broadcast so all clients remove immediately (avoids stale refetch from other PM2 workers)
    broadcastSSE({ type: 'marker_delete', data: { id } });

    return true;
  });
}

/** Delete all markers matching a region (oblast).
 *  Optionally filter by threat_type(s). If placeContains is set, only markers whose
 *  place/location text includes that substring (case-insensitive) are removed. */
export async function deleteByRegion(
  region: string,
  threatTypes?: string[],
  placeContains?: string,
): Promise<number> {
  return withWriteLock(async () => {
    const s = getState();
    const before = s.messages.length;
    const regionLower = region.toLowerCase();
    const placeNeedle =
      placeContains && placeContains.trim().length >= 2
        ? placeContains.trim().toLowerCase()
        : '';
    s.messages = s.messages.filter((m) => {
      const r = ((m.region || m.place_region || '') as string).toLowerCase();
      if (!r.includes(regionLower) && regionLower !== r) return true; // not this region — keep
      if (placeNeedle) {
        const loc = `${(m.place as string) || ''} ${(m.location as string) || ''}`.toLowerCase();
        if (!loc.includes(placeNeedle)) return true; // wrong place — keep
      }
      if (threatTypes && threatTypes.length > 0) {
        const tt = ((m.threat_type || m.type || '') as string).toLowerCase();
        return !threatTypes.some((t) => t.toLowerCase() === tt);
      }
      return false; // remove
    });
    const removed = before - s.messages.length;
    if (removed > 0) {
      await Promise.all([writeToRedis(), persistToDisk()]);
    }
    return removed;
  });
}

// ── Prune ────────────────────────────────────────────────────────────────────

/** Read the admin monitor period (minutes) and add a small buffer for pruning.
 *  Storage keeps markers slightly longer than display TTL so that
 *  slow-polling workers don't lose markers prematurely. */
function getRetentionMs(): number {
  try {
    const settings = loadSettings();
    const monitorMinutes = settings.monitorPeriod || 30;
    // Slightly longer than display TTL so slow workers / refetch do not drop tracks early.
    const retentionMinutes = Math.min(300, monitorMinutes + 15);
    return retentionMinutes * 60 * 1000;
  } catch {
    return RETENTION_HOURS_FALLBACK * 60 * 60 * 1000;
  }
}

function pruneMessages(messages: Record<string, unknown>[]): Record<string, unknown>[] {
  const cutoffMs = Date.now() - getRetentionMs();
  const now = Date.now();

  let activeThreatTtlMs = 35 * 60 * 1000;
  try {
    const settings = loadSettings();
    const monitorMinutes = settings.monitorPeriod || 30;
    activeThreatTtlMs = (monitorMinutes + 5) * 60 * 1000;
  } catch { /* fallback above */ }
  const ACTIVE_THREAT_TYPES = new Set([
    'shahed', 'drone', 'uav', 'fpv', 'rozved',
    'raketa', 'missile', 'pusk', 'launch', 'ballistic',
    'kab', 'rszv', 'avia',
  ]);

  let result = messages.filter((m) => {
    if (m.manual) return true;

    const threatType = (m.threat_type as string) || '';

    // Active moving threats: use aggressive 15-min TTL based on last_update_epoch
    if (ACTIVE_THREAT_TYPES.has(threatType)) {
      const updateEpoch = m.last_update_epoch as number | undefined;
      const createdEpoch = m.created_at_epoch as number | undefined;
      const refEpoch = updateEpoch && updateEpoch > 1000000000 ? updateEpoch
        : createdEpoch && createdEpoch > 1000000000 ? createdEpoch : 0;
      if (refEpoch > 0) {
        const refMs = refEpoch > 10000000000 ? refEpoch : refEpoch * 1000;
        let ttlMs = activeThreatTtlMs;
        const pm = (m.placement_mode as string | undefined) || '';
        // Approximate pins: cap at 60m if stale (predictive uses full activeThreatTtlMs so map/API can show them as long as point tracks)
        if (pm === 'approximate') {
          ttlMs = Math.min(ttlMs, 60 * 60 * 1000);
        }
        return (now - refMs) < ttlMs;
      }
      // No epoch — fall through to legacy ts check
    }

    // For track markers that are still receiving updates, use last_update_epoch
    // so active tracks aren't pruned while still being updated.
    // For tracks that stopped updating, last_update_epoch ages out naturally.
    if (m.track_id && typeof m.last_update_epoch === 'number' && m.last_update_epoch > 1000000000) {
      const updateMs = (m.last_update_epoch as number) > 10000000000
        ? (m.last_update_epoch as number) : (m.last_update_epoch as number) * 1000;
      return updateMs >= cutoffMs;
    }

    // For non-tracked markers or tracks without last_update_epoch:
    // use created_at_epoch (original creation time) for pruning.
    const createdEpoch = m.created_at_epoch as number | undefined;
    if (createdEpoch && createdEpoch > 1000000000) {
      const createdMs = createdEpoch > 10000000000 ? createdEpoch : createdEpoch * 1000;
      return createdMs >= cutoffMs; // definitive — don't fall through to ts
    }

    // Fallback: use ts/date for legacy markers without created_at_epoch.
    // MUST use Date.parse — string comparison breaks with timezone offsets
    // (e.g. "22:15+02:00" > "22:05Z" but the actual time is 2h earlier).
    const ts = (m.ts || m.timestamp || m.date || '') as string;
    if (ts) {
      const normalized = ts.includes('T') ? ts : ts.replace(' ', 'T');
      const parsed = new Date(normalized).getTime();
      if (!isNaN(parsed) && parsed > 0) {
        return parsed >= cutoffMs;
      }
    }
    return true; // no parseable timestamp — keep (shouldn't happen)
  });

  if (result.length > MAX_MESSAGES) {
    // Sort by CREATION time (not last-update time) so oldest markers get dropped first,
    // even if they were recently track-updated.
    result.sort((a, b) => {
      const aEpoch = a.created_at_epoch as number | undefined;
      const bEpoch = b.created_at_epoch as number | undefined;
      const aMs = aEpoch && aEpoch > 1000000000
        ? (aEpoch > 10000000000 ? aEpoch : aEpoch * 1000)
        : new Date((a.ts || a.timestamp || a.date || '') as string).getTime() || 0;
      const bMs = bEpoch && bEpoch > 1000000000
        ? (bEpoch > 10000000000 ? bEpoch : bEpoch * 1000)
        : new Date((b.ts || b.timestamp || b.date || '') as string).getTime() || 0;
      return bMs - aMs; // newest first
    });
    result = result.slice(0, MAX_MESSAGES);
  }

  return result;
}

/** Background prune — called periodically, not on every request. */
const PRUNE_INTERVAL = 60_000;
let _lastPruneTime = 0;

export function maybePrune(): void {
  const now = Date.now();
  if (now - _lastPruneTime < PRUNE_INTERVAL) return;
  _lastPruneTime = now;

  withWriteLock(async () => {
    const s = getState();
    const before = s.messages.length;
    s.messages = pruneMessages(s.messages);
    const removed = before - s.messages.length;
    if (removed > 0) {
      await Promise.all([writeToRedis(), persistToDisk()]);
      console.log(`[STORE] Pruned ${removed} old markers (${s.messages.length} remaining)`);
    }
  }).catch((err) => console.warn('[STORE] Prune error:', err));
}

// ── Redis write ──────────────────────────────────────────────────────────────
async function writeToRedisCore(): Promise<void> {
  if (isRedisDisabledInThisProcess()) return;
  try {
    const s = getState();
    const redis = getRedis();
    const pipeline = redis.pipeline();
    pipeline.set(REDIS_MARKERS_KEY, JSON.stringify(s.messages), 'EX', REDIS_MARKERS_TTL);
    pipeline.incr(REDIS_VERSION_KEY);
    const results = await pipeline.exec();
    // Update local version to match what we just wrote
    if (results && results[1] && results[1][1] != null) {
      s.lastVersion = results[1][1] as number;
    }
    invalidateMarkerDerivedCaches();
  } catch (err) {
    console.warn('[STORE] Redis write failed:', err);
  }
}

async function writeToRedis(): Promise<void> {
  if (_markerPersistDeferDepth > 0) return;
  await writeToRedisCore();
}

// ── Persist to disk (async, non-blocking) ────────────────────────────────────
const BACKUP_COPIES = 3;
let _lastBackupTime = 0;
const BACKUP_INTERVAL = 5 * 60_000; // rotate backups at most every 5 minutes

async function persistToDiskCore(): Promise<void> {
  const filePath = MESSAGES_FILE;
  const dir = path.dirname(filePath);
  try { await fsp.access(dir); } catch { await fsp.mkdir(dir, { recursive: true }); }

  // Rotate backups periodically (keeps messages.json.1, .2, .3)
  const now = Date.now();
  if (now - _lastBackupTime > BACKUP_INTERVAL) {
    _lastBackupTime = now;
    try {
      for (let i = BACKUP_COPIES; i >= 1; i--) {
        const src = i === 1 ? filePath : `${filePath}.${i - 1}`;
        const dst = `${filePath}.${i}`;
        try {
          await fsp.access(src);
          await fsp.copyFile(src, dst);
        } catch { /* source doesn't exist, skip */ }
      }
    } catch (err) {
      console.warn('[STORE] Backup rotation error:', err);
    }
  }

  const tmp = filePath + '.tmp.' + crypto.randomBytes(4).toString('hex');
  await fsp.writeFile(tmp, JSON.stringify(getState().messages), 'utf-8');
  await fsp.rename(tmp, filePath);
}

async function persistToDisk(): Promise<void> {
  if (_markerPersistDeferDepth > 0) return;
  await persistToDiskCore();
}
