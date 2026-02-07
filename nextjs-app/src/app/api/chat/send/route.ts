import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';
import { broadcastSSE } from '../stream/route';

const DATA_DIR = process.env.DATA_DIR || '/data';
const CHAT_FILE = path.join(DATA_DIR, 'chat_messages.json');
const FALLBACK_CHAT_FILE = path.resolve(process.cwd(), '..', 'chat_messages.json');

const MAX_MESSAGE_LENGTH = 500;
const MAX_MESSAGES = 1000;

// Simple rate limiter
const rateLimiter = new Map<string, number>();
const RATE_LIMIT_MS = 3000;

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function loadMessages(filePath: string): any[] {
  try {
    if (fs.existsSync(filePath)) {
      const raw = fs.readFileSync(filePath, 'utf-8');
      const data = JSON.parse(raw);
      return Array.isArray(data) ? data : data.messages || [];
    }
  } catch { /* start fresh */ }
  return [];
}

export async function POST(request: Request) {
  try {
    const body = await request.json();

    // Accept both Flutter format (userId/deviceId/message) and new format (device_id/nickname/text)
    const userId = body.userId || body.nickname || body.user_id;
    const deviceId = body.deviceId || body.device_id;
    const text = body.message || body.text;
    const replyToId = body.replyTo; // message ID string

    if (!deviceId || !text) {
      return NextResponse.json({ error: 'Missing required fields' }, { status: 400 });
    }

    if (text.length > MAX_MESSAGE_LENGTH) {
      return NextResponse.json({ error: 'Message too long' }, { status: 400 });
    }

    // Rate limiting
    const lastSent = rateLimiter.get(deviceId) || 0;
    if (Date.now() - lastSent < RATE_LIMIT_MS) {
      return NextResponse.json({ error: 'Rate limited' }, { status: 429 });
    }
    rateLimiter.set(deviceId, Date.now());

    // Check ban
    const banFile = path.join(DATA_DIR, 'chat_bans.json');
    try {
      if (fs.existsSync(banFile)) {
        const bans = JSON.parse(fs.readFileSync(banFile, 'utf-8'));
        if (Array.isArray(bans) && bans.some((b: { deviceId?: string }) => b.deviceId === deviceId)) {
          return NextResponse.json({ error: 'Ви заблоковані' }, { status: 403 });
        }
      }
    } catch { /* ignore */ }

    const filePath = fs.existsSync(path.dirname(CHAT_FILE)) ? CHAT_FILE : FALLBACK_CHAT_FILE;
    let messages = loadMessages(filePath);

    // Build replyTo object if replying
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let replyTo: any = null;
    if (replyToId) {
      const original = messages.find((m) => m.id === replyToId);
      if (original) {
        replyTo = {
          id: original.id,
          userId: original.userId || original.nickname || 'Анонім',
          message: original.message || original.text || '',
        };
      }
    }

    // Check moderator status
    const modFile = path.join(DATA_DIR, 'chat_moderators.json');
    let isModerator = false;
    try {
      if (fs.existsSync(modFile)) {
        const mods = JSON.parse(fs.readFileSync(modFile, 'utf-8'));
        if (Array.isArray(mods) && mods.includes(deviceId)) {
          isModerator = true;
        }
      }
    } catch { /* ignore */ }

    const now = Date.now() / 1000; // epoch seconds
    const nowDate = new Date();

    // Create message in Flutter-compatible format
    const message = {
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      userId: userId || 'Анонім',
      deviceId,
      message: text.trim(),
      timestamp: now,
      time: `${nowDate.getHours().toString().padStart(2, '0')}:${nowDate.getMinutes().toString().padStart(2, '0')}`,
      date: `${nowDate.getDate().toString().padStart(2, '0')}.${(nowDate.getMonth() + 1).toString().padStart(2, '0')}.${nowDate.getFullYear()}`,
      isModerator,
      replyTo,
      reactions: {},
    };

    messages.push(message);
    if (messages.length > MAX_MESSAGES) {
      messages = messages.slice(-MAX_MESSAGES);
    }

    fs.writeFileSync(filePath, JSON.stringify(messages, null, 2), 'utf-8');

    // Broadcast via SSE
    broadcastSSE({ type: 'new_message', data: message });

    return NextResponse.json({ status: 'ok', message });
  } catch (err) {
    console.error('[CHAT] Send error:', err);
    return NextResponse.json({ error: 'Internal error' }, { status: 500 });
  }
}
