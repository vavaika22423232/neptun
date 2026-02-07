import { NextResponse } from 'next/server';
import { cache } from '@/lib/cache';
import fs from 'fs';
import path from 'path';
import type { ChatMessage } from '@/types';

const DATA_DIR = process.env.DATA_DIR || '/data';
const CHAT_FILE = path.join(DATA_DIR, 'chat_messages.json');
const FALLBACK_CHAT_FILE = path.resolve(process.cwd(), '..', 'chat_messages.json');

const MAX_MESSAGE_LENGTH = 500;
const MAX_MESSAGES = 1000;

// Simple rate limiter
const rateLimiter = new Map<string, number>();
const RATE_LIMIT_MS = 3000; // 3 seconds between messages

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { device_id, nickname, text } = body;

    if (!device_id || !text) {
      return NextResponse.json({ error: 'Missing required fields' }, { status: 400 });
    }

    if (text.length > MAX_MESSAGE_LENGTH) {
      return NextResponse.json({ error: 'Message too long' }, { status: 400 });
    }

    // Rate limiting
    const lastSent = rateLimiter.get(device_id) || 0;
    if (Date.now() - lastSent < RATE_LIMIT_MS) {
      return NextResponse.json({ error: 'Rate limited' }, { status: 429 });
    }
    rateLimiter.set(device_id, Date.now());

    // Create message
    const message: ChatMessage = {
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      device_id,
      nickname: nickname || 'Анонім',
      text: text.trim(),
      timestamp: new Date().toISOString(),
      reactions: {},
    };

    // Save to file
    const filePath = fs.existsSync(path.dirname(CHAT_FILE)) ? CHAT_FILE : FALLBACK_CHAT_FILE;
    let messages: ChatMessage[] = [];
    try {
      if (fs.existsSync(filePath)) {
        const raw = fs.readFileSync(filePath, 'utf-8');
        const data = JSON.parse(raw);
        messages = Array.isArray(data) ? data : data.messages || [];
      }
    } catch {
      // start fresh
    }

    messages.push(message);

    // Keep only last MAX_MESSAGES
    if (messages.length > MAX_MESSAGES) {
      messages = messages.slice(-MAX_MESSAGES);
    }

    fs.writeFileSync(filePath, JSON.stringify(messages, null, 2), 'utf-8');

    // Invalidate cache
    cache.delete('chat_messages');

    return NextResponse.json({ status: 'ok', message });
  } catch (err) {
    console.error('[CHAT] Send error:', err);
    return NextResponse.json({ error: 'Internal error' }, { status: 500 });
  }
}
