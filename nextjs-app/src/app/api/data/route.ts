import { NextResponse } from 'next/server';
import { cache, withETag } from '@/lib/cache';
import fs from 'fs';
import path from 'path';
import type { Marker } from '@/types';

const CACHE_KEY = 'data_markers';
const CACHE_TTL = 2_000; // 2 seconds (matches Flask bg updater interval)
const STALE_TTL = 300_000; // 5 minutes

// Path to shared messages.json (written by Python worker)
const DATA_DIR = process.env.DATA_DIR || '/data';
const MESSAGES_FILE = path.join(DATA_DIR, 'messages.json');
const FALLBACK_MESSAGES_FILE = path.resolve(process.cwd(), '..', 'messages.json');

/**
 * Load markers from the shared messages.json file
 * (written by the Python Telegram worker)
 */
function loadMessagesFromFile(): Marker[] {
  const filePaths = [MESSAGES_FILE, FALLBACK_MESSAGES_FILE];

  for (const filePath of filePaths) {
    try {
      if (fs.existsSync(filePath)) {
        const raw = fs.readFileSync(filePath, 'utf-8');
        const data = JSON.parse(raw);

        // messages.json can be an array or object with .messages
        const messages = Array.isArray(data) ? data : data.messages || [];

        // Transform to Marker format
        return messages
          .filter((m: Record<string, unknown>) => m.lat && m.lng)
          .map((m: Record<string, unknown>) => ({
            id: m.id as string,
            lat: Number(m.lat),
            lng: Number(m.lng),
            threat_type: (m.threat_type || m.type || 'default') as string,
            place: (m.place || m.city || '') as string,
            text: (m.text || '') as string,
            date: (m.date || m.timestamp || '') as string,
            count: (m.count || 1) as number,
            marker_icon: (m.marker_icon || '') as string,
            course_bearing: (m.course_bearing as number) || null,
            course_direction: (m.course_direction || '') as string,
            distance_km: (m.distance_km as number) || undefined,
            speed_kmh: (m.speed_kmh as number) || undefined,
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

export async function GET(request: Request) {
  const clientETag = request.headers.get('If-None-Match');

  // Check cache
  const { entry, isStale } = cache.getWithStale<{ tracks: Marker[]; ballistic_threat: null }>(CACHE_KEY, STALE_TTL);

  if (entry && !isStale) {
    return withETag(entry.data, entry.etag, clientETag);
  }

  // Load fresh data from file
  const markers = loadMessagesFromFile();
  const responseData = {
    tracks: markers,
    ballistic_threat: null, // TODO: read from shared state
  };

  const newEntry = cache.set(CACHE_KEY, responseData, CACHE_TTL);
  return withETag(newEntry.data, newEntry.etag, clientETag);
}
