import { cache, withETag } from '@/lib/cache';
import { buildMarkerOptionsForApi, buildMarkers } from '@/lib/build-markers';
import { initTargetStore, syncTargetStoreFromRedis } from '@/lib/tracked-target-store';

const CACHE_KEY = 'messages_mobile';
const CACHE_TTL = 30_000; // 30 seconds
const STALE_TTL = 300_000; // 5 minutes

interface MobileMessage {
  location: string;
  text: string;
  timestamp: string;
  type: string;
}

function buildMessages(): { messages: MobileMessage[] } {
  const markers = buildMarkers(buildMarkerOptionsForApi(true));

  const recent = markers.slice(0, 50).map((m) => ({
    location: m.region || m.place || '',
    text: (m.text || '') as string,
    timestamp: m.date || '',
    type: (m.threat_type || m.type || '') as string,
  }));

  return { messages: recent };
}

/**
 * GET /api/messages
 * Returns recent parsed messages for the mobile app's alarm timer widget.
 * Zero file I/O — reads from in-memory track store.
 */
export async function GET(request: Request) {
  const clientETag = request.headers.get('If-None-Match');
  await initTargetStore();
  await syncTargetStoreFromRedis();

  // Check cache
  const { entry, isStale } = cache.getWithStale<{ messages: MobileMessage[] }>(CACHE_KEY, STALE_TTL);

  if (entry && !isStale) {
    return withETag(entry.data, entry.etag, clientETag, undefined, entry.json);
  }

  // Build from in-memory store (zero I/O)
  const data = buildMessages();
  const newEntry = cache.set(CACHE_KEY, data, CACHE_TTL);
  return withETag(newEntry.data, newEntry.etag, clientETag, undefined, newEntry.json);
}
