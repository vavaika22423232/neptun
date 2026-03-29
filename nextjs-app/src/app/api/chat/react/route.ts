import { NextResponse } from 'next/server';
import fs from 'fs';
import fsp from 'fs/promises';
import path from 'path';
import crypto from 'crypto';
import { broadcastSSE } from '../stream/route';
import { isBanned } from '@/lib/admin/data';

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

import { getJwtSecret } from '@/lib/server-secrets';
import { verifyChatToken } from '@/lib/chat-auth';

export async function POST(request: Request) {
  try {
    const authHeader = request.headers.get('Authorization') || '';
    const token = authHeader.split(' ')[1];
    const jwtSecret = getJwtSecret();

    if (!token || !jwtSecret) {
      return NextResponse.json({ error: 'Потрібна авторизація' }, { status: 401 });
    }

    const payload = verifyChatToken(token, jwtSecret);
    if (!payload || payload.type !== 'access') {
      return NextResponse.json({ error: 'Сесія недійсна' }, { status: 401 });
    }

    const body = await request.json();

    const messageId = body.messageId || body.message_id;
    const emoji = body.emoji || body.reaction;
    
    // IDENTITY: Exclusively from JWT!
    const deviceId = payload.deviceId;
    const nickname = payload.nickname || 'Анонім';
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

      return { ok: true as const, reactions: msg.reactions };
    });

    if ('error' in result) {
      return NextResponse.json({ error: result.error }, { status: 404 });
    }

    broadcastSSE({
      type: 'reaction',
      data: { messageId, reactions: result.reactions },
    });

    return NextResponse.json({ status: 'ok', reactions: result.reactions });
  } catch (err) {
    console.error('[CHAT] React error:', err);
    return NextResponse.json({ error: 'Internal error' }, { status: 500 });
  }
}
