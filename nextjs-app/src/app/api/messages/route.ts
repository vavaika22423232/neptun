import { cache, withETag } from '@/lib/cache';
import { getRawMessages } from '@/lib/markers-store';

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
  const messages = getRawMessages();

  // Return last 50 messages, formatted for mobile
  const recent = messages.slice(-50).reverse().map((m) => ({
    location: (m.region || m.location || m.place || '') as string,
    text: (m.text || '') as string,
    timestamp: (m.ts || m.date || m.timestamp || '') as string,
    type: (m.threat_type || m.type || '') as string,
  }));

  return { messages: recent };
}

/**
 * GET /api/messages
 * Returns recent parsed messages for the mobile app's alarm timer widget.
 * Zero file I/O — reads from in-memory markers-store.
 */
export async function GET(request: Request) {
  const clientETag = request.headers.get('If-None-Match');

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
