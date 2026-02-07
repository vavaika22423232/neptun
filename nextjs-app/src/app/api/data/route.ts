import { NextResponse } from 'next/server';
import { cache, withETag } from '@/lib/cache';
import fs from 'fs';
import path from 'path';
import type { Marker } from '@/types';
import { loadSettings, loadHidden } from '@/lib/admin/data';

const CACHE_KEY = 'data_markers';
const CACHE_TTL = 2_000; // 2 seconds
const STALE_TTL = 300_000; // 5 minutes

// Path to shared messages.json (written by Python worker via /api/ingest)
const DATA_DIR = process.env.DATA_DIR || '/data';
const MESSAGES_FILE = path.join(DATA_DIR, 'messages.json');
const FALLBACK_MESSAGES_FILE = path.resolve(process.cwd(), '..', 'messages.json');

// Retention config (must match /api/ingest)
const RETENTION_HOURS = 3;
const MAX_MESSAGES = 500;
const PRUNE_INTERVAL = 60_000; // only prune at most once per minute
let _lastPruneTime = 0;

/**
 * Load markers from the shared messages.json file,
 * filtering by monitorPeriod and hidden list.
 */
function loadMessagesFromFile(): Marker[] {
  const filePaths = [MESSAGES_FILE, FALLBACK_MESSAGES_FILE];

  // Load settings
  let monitorMinutes = 30;
  let ttlEnabled = true;
  try {
    const settings = loadSettings();
    monitorMinutes = settings.monitorPeriod || 30;
    ttlEnabled = settings.ttlEnabled;
  } catch { /* use defaults */ }

  // Load hidden markers set
  let hiddenSet: Set<string> = new Set();
  try {
    const hiddenList = loadHidden();
    hiddenSet = new Set(hiddenList);
  } catch { /* empty set */ }

  const cutoffMs = ttlEnabled ? Date.now() - monitorMinutes * 60 * 1000 : 0;

  for (const filePath of filePaths) {
    try {
      if (fs.existsSync(filePath)) {
        const raw = fs.readFileSync(filePath, 'utf-8');
        const data = JSON.parse(raw);

        // messages.json can be an array or object with .messages
        const messages = Array.isArray(data) ? data : data.messages || [];

        return messages
          .filter((m: Record<string, unknown>) => {
            // Must have coordinates
            if (!m.lat || !m.lng) return false;

            // Filter by TTL/monitorPeriod
            if (ttlEnabled && cutoffMs > 0) {
              const msgTime = parseMessageTime(m);
              if (msgTime > 0 && msgTime < cutoffMs) return false;
            }

            // Filter hidden markers
            const hiddenKey = `${m.lat},${m.lng}|${m.text || ''}|${m.manual ? 'manual' : 'auto'}`;
            if (hiddenSet.has(hiddenKey)) return false;

            // Filter low-confidence rejected markers
            if (m.hidden === true) return false;

            return true;
          })
          .map((m: Record<string, unknown>) => ({
            id: m.id as string,
            lat: Number(m.lat),
            lng: Number(m.lng),
            threat_type: (m.threat_type || m.type || 'default') as string,
            place: (m.place || m.city || m.location || '') as string,
            text: (m.text || '') as string,
            date: (m.date || m.timestamp || m.ts || '') as string,
            count: (m.count || 1) as number,
            marker_icon: (m.marker_icon || '') as string,
            course_bearing: (m.course_bearing as number) || null,
            course_direction: (m.course_direction || '') as string,
            distance_km: (m.distance_km as number) || undefined,
            speed_kmh: (m.speed_kmh as number) || undefined,
            confidence: (m.confidence as number) || undefined,
            resolve_status: (m.resolve_status || '') as string,
            trajectory: m.trajectory ? {
              start: (m.trajectory as Record<string, unknown>).start as [number, number] | undefined,
              end: (m.trajectory as Record<string, unknown>).end as [number, number] | undefined,
              predicted: (m.trajectory as Record<string, unknown>).predicted as boolean | undefined,
            } : null,
          }));
      }
    } catch (err) {
      console.warn(`[DATA] Failed to read ${filePath}:`, err);
    }
  }

  return [];
}

/**
 * Prune old messages directly from messages.json on disk.
 * Runs at most once per PRUNE_INTERVAL to avoid excessive I/O.
 * This ensures stale markers are cleaned up even when the worker is offline.
 */
function pruneOldMessagesOnDisk(): void {
  const now = Date.now();
  if (now - _lastPruneTime < PRUNE_INTERVAL) return;
  _lastPruneTime = now;

  const filePath = fs.existsSync(MESSAGES_FILE) ? MESSAGES_FILE
    : fs.existsSync(FALLBACK_MESSAGES_FILE) ? FALLBACK_MESSAGES_FILE
    : null;
  if (!filePath) return;

  try {
    const raw = fs.readFileSync(filePath, 'utf-8');
    const data = JSON.parse(raw);
    const messages: Record<string, unknown>[] = Array.isArray(data) ? data : [];
    if (messages.length === 0) return;

    const cutoff = new Date(now - RETENTION_HOURS * 60 * 60 * 1000).toISOString();
    let result = messages.filter((m) => {
      if (m.manual) return true;
      const ts = (m.ts || m.timestamp || m.date || '') as string;
      if (ts && ts < cutoff) return false;
      return true;
    });

    // Cap at MAX_MESSAGES (keep newest)
    if (result.length > MAX_MESSAGES) {
      result.sort((a, b) => {
        const aTs = (a.ts || a.timestamp || a.date || '') as string;
        const bTs = (b.ts || b.timestamp || b.date || '') as string;
        return bTs.localeCompare(aTs);
      });
      result = result.slice(0, MAX_MESSAGES);
    }

    const removed = messages.length - result.length;
    if (removed > 0) {
      const dir = path.dirname(filePath);
      const tmpFile = filePath + '.tmp';
      fs.writeFileSync(tmpFile, JSON.stringify(result, null, 2), 'utf-8');
      fs.renameSync(tmpFile, filePath);
      console.log(`[DATA] Pruned ${removed} old markers (${result.length} remaining)`);
    }
  } catch (err) {
    console.warn('[DATA] Failed to prune old messages:', err);
  }
}

/** Parse message timestamp from various formats */
function parseMessageTime(m: Record<string, unknown>): number {
  // Try ISO string (ts field from worker)
  const ts = (m.ts || m.timestamp || m.date || '') as string;
  if (ts) {
    const parsed = new Date(ts).getTime();
    if (!isNaN(parsed) && parsed > 0) return parsed;
  }
  // Try unix timestamp
  const unix = m.unix_ts || m.created_at;
  if (typeof unix === 'number' && unix > 1000000000) {
    return unix > 10000000000 ? unix : unix * 1000; // seconds vs ms
  }
  return 0; // unknown = don't filter
}

export async function GET(request: Request) {
  const clientETag = request.headers.get('If-None-Match');

  // Periodically prune stale markers from disk (max once per minute)
  pruneOldMessagesOnDisk();

  // Check cache
  const { entry, isStale } = cache.getWithStale<{ tracks: Marker[]; ballistic_threat: null }>(CACHE_KEY, STALE_TTL);

  if (entry && !isStale) {
    return withETag(entry.data, entry.etag, clientETag);
  }

  // Load fresh data from file (with filtering)
  const markers = loadMessagesFromFile();
  const responseData = {
    tracks: markers,
    ballistic_threat: null,
  };

  const newEntry = cache.set(CACHE_KEY, responseData, CACHE_TTL);
  return withETag(newEntry.data, newEntry.etag, clientETag);
}
