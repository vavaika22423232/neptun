import { NextResponse } from 'next/server';
import fs from 'fs';
import fsp from 'fs/promises';
import path from 'path';
import crypto from 'crypto';
import { broadcastSSE } from '@/lib/chat-sse-stream';
import { isBanned } from '@/lib/admin/data';
import { invalidateChatCache } from '../messages/route';

const DATA_DIR = process.env.DATA_DIR || '/data';
const CHAT_FILE = path.join(DATA_DIR, 'chat_messages.json');
const FALLBACK_CHAT_FILE = path.resolve(process.cwd(), '..', 'chat_messages.json');

// Simple write lock for chat file
let _chatLock: Promise<void> = Promise.resolve();
function withChatLock<T>(fn: () => Promise<T>): Promise<T> {
  const prev = _chatLock;
  let resolve!: () => void;
  _chatLock = new Promise<void>((r) => { resolve = r; });
  return prev.then(fn).finally(() => resolve());
}

interface ReactionInfo {
  deviceId: string;
  nickname: string;
  timestamp: number;
}

import { requireChatAuth } from '@/lib/chat-auth';

export async function POST(request: Request) {
  try {
    const authResult = requireChatAuth(request);
    if (authResult instanceof Response) return authResult;
    const identity = authResult;

    const body = await request.json();

    const messageId = body.messageId || body.message_id;
    const emoji = body.emoji || body.reaction;
    
    const deviceId = identity.deviceId;
    const nickname = identity.nickname.slice(0, 30);
    const hardwareId = body.hardwareId || body.hardware_id;

    // Block banned users from reacting
    if (isBanned(deviceId, nickname, hardwareId)) {
      return NextResponse.json({ error: 'Ви заблоковані' }, { status: 403 });
    }

    if (!messageId || !emoji) {
      return NextResponse.json({ error: 'Missing fields' }, { status: 400 });
    }

    const result = await withChatLock(async () => {
      const filePath = fs.existsSync(path.dirname(CHAT_FILE)) ? CHAT_FILE : FALLBACK_CHAT_FILE;
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      let messages: any[] = [];

      try {
        const raw = await fsp.readFile(filePath, 'utf-8');
        const data = JSON.parse(raw);
        messages = Array.isArray(data) ? data : data.messages || [];
      } catch {
        return { error: 'No messages' as const };
      }

      const msg = messages.find((m: { id: string }) => m.id === messageId);
      if (!msg) {
        return { error: 'Message not found' as const };
      }

      if (!msg.reactions) msg.reactions = {};
      if (!Array.isArray(msg.reactions[emoji])) {
        msg.reactions[emoji] = [];
      }

      const reactionList = msg.reactions[emoji] as ReactionInfo[];
      const existingIdx = reactionList.findIndex((r: ReactionInfo) => r.deviceId === deviceId);
      if (existingIdx >= 0) {
        reactionList.splice(existingIdx, 1);
        if (reactionList.length === 0) {
          delete msg.reactions[emoji];
        }
      } else {
        reactionList.push({ deviceId, nickname, timestamp: Date.now() / 1000 });
      }

      // Async write with atomic rename
      const tmp = filePath + '.tmp.' + crypto.randomBytes(4).toString('hex');
      await fsp.writeFile(tmp, JSON.stringify(messages, null, 2), 'utf-8');
      await fsp.rename(tmp, filePath);
      invalidateChatCache();

      return { ok: true as const, reactions: msg.reactions };
    });

    if ('error' in result) {
      return NextResponse.json({ error: result.error }, { status: 404 });
    }

    const cleanReactions: Record<string, unknown> = {};
    for (const [emoji, list] of Object.entries(result.reactions as Record<string, unknown[]>)) {
      if (Array.isArray(list)) {
        cleanReactions[emoji] = list.map((r: unknown) => {
          if (r && typeof r === 'object') {
            const { deviceId: _d, ...safe } = r as Record<string, unknown>;
            return safe;
          }
          return r;
        });
      }
    }

    broadcastSSE({
      type: 'reaction',
      data: { messageId, reactions: cleanReactions },
    });

    return NextResponse.json({ status: 'ok', reactions: cleanReactions });
  } catch (err) {
    console.error('[CHAT] React error:', err);
    return NextResponse.json({ error: 'Internal error' }, { status: 500 });
  }
}
