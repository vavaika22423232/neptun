/**
 * Short-lived in-memory cache for chat_messages.json reads.
 * invalidateChatCache() clears this process and notifies other PM2 workers via Redis.
 */

import { publishChatCacheInvalidate } from '@/lib/redis';

let _chatCache: { messages: unknown[]; ts: number } | null = null;

/** Exported for messages/route — reset when file is read (same TTL semantics). */
export function setChatMessagesCache(messages: unknown[], ts: number) {
  _chatCache = { messages, ts };
}

export function getChatMessagesCache(): { messages: unknown[]; ts: number } | null {
  return _chatCache;
}

export function clearChatMessagesCacheLocal() {
  _chatCache = null;
}

/** Call after any write to chat_messages.json — all Node workers drop their cache. */
export function invalidateChatCache() {
  clearChatMessagesCacheLocal();
  publishChatCacheInvalidate().catch(() => {
    /* Redis optional — local invalidation still applied */
  });
}
