import { NextResponse } from 'next/server';
import fsp from 'fs/promises';
import path from 'path';
import {
  getChatMessagesCache,
  setChatMessagesCache,
  invalidateChatCache,
} from '@/lib/chat-messages-cache';

const DATA_DIR = process.env.DATA_DIR || '/data';
const CHAT_FILE = path.join(DATA_DIR, 'chat_messages.json');
const FALLBACK_CHAT_FILE = path.resolve(process.cwd(), '..', 'chat_messages.json');

const CHAT_CACHE_TTL = 2_000;

async function loadChatMessages(): Promise<unknown[]> {
  const cached = getChatMessagesCache();
  if (cached && Date.now() - cached.ts < CHAT_CACHE_TTL) {
    return cached.messages;
  }

  for (const filePath of [CHAT_FILE, FALLBACK_CHAT_FILE]) {
    try {
      const raw = await fsp.readFile(filePath, 'utf-8');
      const data = JSON.parse(raw);
      const messages = Array.isArray(data) ? data : data.messages || [];
      setChatMessagesCache(messages, Date.now());
      return messages;
    } catch {
      // try next
    }
  }
  return [];
}

/** @deprecated Import from @/lib/chat-messages-cache — kept for older imports */
export { invalidateChatCache };

const SSE_GATEWAY_URL = process.env.SSE_GATEWAY_URL || 'http://127.0.0.1:4000';

async function fetchRealOnlineCount(): Promise<number> {
  try {
    const res = await fetch(`${SSE_GATEWAY_URL}/health`, {
      signal: AbortSignal.timeout(2000),
    });
    if (res.ok) {
      const data = (await res.json()) as { clients?: number };
      const n = typeof data.clients === 'number' ? data.clients : 0;
      return Math.max(n, 0);
    }
  } catch {
    // Gateway may be down, use fallback
  }
  return -1;
}

import { requireChatAuth } from '@/lib/chat-auth';

export async function GET(request: Request) {
  const authResult = requireChatAuth(request);
  if (authResult instanceof Response) return authResult;

  const messages = await loadChatMessages();
  const { searchParams } = new URL(request.url);
  const beforeParam = searchParams.get('before');
  const limitParam = searchParams.get('limit');
  const limit = beforeParam
    ? Math.min(parseInt(limitParam || '50', 10) || 50, 100)
    : 200;
  let recent: unknown[];
  if (beforeParam) {
    const before = parseFloat(beforeParam);
    const older = (messages as Record<string, unknown>[]).filter((m) => {
      const ts = typeof m.timestamp === 'number' ? m.timestamp : (m.timestamp as string) ? parseFloat(String(m.timestamp)) : 0;
      return ts < before;
    });
    recent = older.slice(-limit);
  } else {
    recent = messages.slice(-limit);
  }

  const realOnline = await fetchRealOnlineCount();
  const oneHourAgo = Date.now() / 1000 - 3600;
  const recentUsers = new Set(
    (recent as Record<string, unknown>[])
      .filter((m) => {
        const ts = typeof m.timestamp === 'number' ? m.timestamp : Date.now() / 1000;
        return ts > oneHourAgo;
      })
      .map((m) => m.userId || m.deviceId || m.device_id)
  );
  const fallbackOnline = Math.max(recentUsers.size, 1);
  const online = realOnline >= 0 ? realOnline : fallbackOnline;

  // Keep message.deviceId so clients can mark "my" bubbles (Flutter: deviceId == myDeviceId).
  // Stripping it broke isMine when userId was "Анонім" or differed from local prefs.
  const sanitized = (recent as Record<string, unknown>[]).map((m) => {
    const safe = { ...m } as Record<string, unknown>;
    if (safe.device_id && !safe.deviceId) {
      safe.deviceId = safe.device_id;
    }
    delete safe.device_id;
    if (safe.replyTo && typeof safe.replyTo === 'object') {
      const { deviceId: _, device_id: __, ...safeReply } = safe.replyTo as Record<string, unknown>;
      safe.replyTo = safeReply;
    }
    if (safe.reactions && typeof safe.reactions === 'object') {
      const cleanReactions: Record<string, unknown> = {};
      for (const [emoji, list] of Object.entries(safe.reactions as Record<string, unknown[]>)) {
        if (Array.isArray(list)) {
          cleanReactions[emoji] = list.map((r: unknown) => {
            if (r && typeof r === 'object') {
              const { deviceId: _d, ...safeR } = r as Record<string, unknown>;
              return safeR;
            }
            return r;
          });
        }
      }
      safe.reactions = cleanReactions;
    }
    return safe;
  });

  return NextResponse.json({
    messages: sanitized,
    online: Math.max(online, 1),
  });
}
