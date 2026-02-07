import { NextResponse } from 'next/server';
import { cache } from '@/lib/cache';
import fs from 'fs';
import path from 'path';
import type { ChatMessage } from '@/types';

const DATA_DIR = process.env.DATA_DIR || '/data';
const CHAT_FILE = path.join(DATA_DIR, 'chat_messages.json');
const FALLBACK_CHAT_FILE = path.resolve(process.cwd(), '..', 'chat_messages.json');

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { message_id, reaction, device_id } = body;

    if (!message_id || !reaction) {
      return NextResponse.json({ error: 'Missing fields' }, { status: 400 });
    }

    const filePath = fs.existsSync(path.dirname(CHAT_FILE)) ? CHAT_FILE : FALLBACK_CHAT_FILE;
    let messages: ChatMessage[] = [];

    try {
      if (fs.existsSync(filePath)) {
        const raw = fs.readFileSync(filePath, 'utf-8');
        const data = JSON.parse(raw);
        messages = Array.isArray(data) ? data : data.messages || [];
      }
    } catch {
      return NextResponse.json({ error: 'No messages' }, { status: 404 });
    }

    const msg = messages.find((m) => m.id === message_id);
    if (!msg) {
      return NextResponse.json({ error: 'Message not found' }, { status: 404 });
    }

    if (!msg.reactions) msg.reactions = {};
    msg.reactions[reaction] = (msg.reactions[reaction] || 0) + 1;

    fs.writeFileSync(filePath, JSON.stringify(messages, null, 2), 'utf-8');
    cache.delete('chat_messages');

    return NextResponse.json({ status: 'ok', reactions: msg.reactions });
  } catch (err) {
    console.error('[CHAT] React error:', err);
    return NextResponse.json({ error: 'Internal error' }, { status: 500 });
  }
}
