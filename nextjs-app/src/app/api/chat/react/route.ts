import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';
import { broadcastSSE } from '../stream/route';

const DATA_DIR = process.env.DATA_DIR || '/data';
const CHAT_FILE = path.join(DATA_DIR, 'chat_messages.json');
const FALLBACK_CHAT_FILE = path.resolve(process.cwd(), '..', 'chat_messages.json');

interface ReactionInfo {
  deviceId: string;
  nickname: string;
  timestamp: number;
}

export async function POST(request: Request) {
  try {
    const body = await request.json();

    // Accept both Flutter format (messageId/emoji/deviceId/nickname) and old format (message_id/reaction/device_id)
    const messageId = body.messageId || body.message_id;
    const emoji = body.emoji || body.reaction;
    const deviceId = body.deviceId || body.device_id;
    const nickname = body.nickname || 'Анонім';

    if (!messageId || !emoji) {
      return NextResponse.json({ error: 'Missing fields' }, { status: 400 });
    }

    const filePath = fs.existsSync(path.dirname(CHAT_FILE)) ? CHAT_FILE : FALLBACK_CHAT_FILE;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    let messages: any[] = [];

    try {
      if (fs.existsSync(filePath)) {
        const raw = fs.readFileSync(filePath, 'utf-8');
        const data = JSON.parse(raw);
        messages = Array.isArray(data) ? data : data.messages || [];
      }
    } catch {
      return NextResponse.json({ error: 'No messages' }, { status: 404 });
    }

    const msg = messages.find((m) => m.id === messageId);
    if (!msg) {
      return NextResponse.json({ error: 'Message not found' }, { status: 404 });
    }

    // Reactions stored as Record<string, ReactionInfo[]>
    if (!msg.reactions) msg.reactions = {};
    if (!Array.isArray(msg.reactions[emoji])) {
      // Migrate from old counter format if needed
      msg.reactions[emoji] = [];
    }

    const reactionList = msg.reactions[emoji] as ReactionInfo[];

    // Toggle: if user already reacted with this emoji, remove it
    const existingIdx = reactionList.findIndex((r: ReactionInfo) => r.deviceId === deviceId);
    if (existingIdx >= 0) {
      reactionList.splice(existingIdx, 1);
      if (reactionList.length === 0) {
        delete msg.reactions[emoji];
      }
    } else {
      reactionList.push({
        deviceId,
        nickname,
        timestamp: Date.now() / 1000,
      });
    }

    fs.writeFileSync(filePath, JSON.stringify(messages, null, 2), 'utf-8');

    // Broadcast via SSE
    broadcastSSE({
      type: 'reaction',
      data: { messageId, reactions: msg.reactions },
    });

    return NextResponse.json({ status: 'ok', reactions: msg.reactions });
  } catch (err) {
    console.error('[CHAT] React error:', err);
    return NextResponse.json({ error: 'Internal error' }, { status: 500 });
  }
}
