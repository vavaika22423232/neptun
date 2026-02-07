import { NextResponse } from 'next/server';
import { cache, withETag } from '@/lib/cache';
import fs from 'fs';
import path from 'path';
import type { ChatMessage } from '@/types';

const CACHE_KEY = 'chat_messages';
const CACHE_TTL = 5_000; // 5 seconds

const DATA_DIR = process.env.DATA_DIR || '/data';
const CHAT_FILE = path.join(DATA_DIR, 'chat_messages.json');
const FALLBACK_CHAT_FILE = path.resolve(process.cwd(), '..', 'chat_messages.json');

function loadChatMessages(): ChatMessage[] {
  for (const filePath of [CHAT_FILE, FALLBACK_CHAT_FILE]) {
    try {
      if (fs.existsSync(filePath)) {
        const raw = fs.readFileSync(filePath, 'utf-8');
        const data = JSON.parse(raw);
        return Array.isArray(data) ? data : data.messages || [];
      }
    } catch {
      // ignore
    }
  }
  return [];
}

export async function GET(request: Request) {
  const clientETag = request.headers.get('If-None-Match');

  const { entry } = cache.getWithStale<ChatMessage[]>(CACHE_KEY, 60_000);
  if (entry) {
    return withETag(entry.data, entry.etag, clientETag);
  }

  const messages = loadChatMessages();
  // Return last 100 messages
  const recent = messages.slice(-100);
  const newEntry = cache.set(CACHE_KEY, recent, CACHE_TTL);
  return withETag(newEntry.data, newEntry.etag, clientETag);
}
