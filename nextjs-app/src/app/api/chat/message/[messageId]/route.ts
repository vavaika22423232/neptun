import { NextResponse } from 'next/server';
import { cache } from '@/lib/cache';
import fs from 'fs';
import path from 'path';
import type { ChatMessage } from '@/types';

const DATA_DIR = process.env.DATA_DIR || '/data';
const CHAT_FILE = path.join(DATA_DIR, 'chat_messages.json');
const FALLBACK_CHAT_FILE = path.resolve(process.cwd(), '..', 'chat_messages.json');

/**
 * DELETE /api/chat/message/[messageId]
 * Delete a chat message by ID (moderator or message author).
 */
export async function DELETE(
  request: Request,
  { params }: { params: Promise<{ messageId: string }> }
) {
  try {
    const { messageId } = await params;
    const body = await request.json().catch(() => ({}));
    const deviceId = (body as Record<string, string>).deviceId || '';

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

    const msgIdx = messages.findIndex((m) => m.id === messageId);
    if (msgIdx === -1) {
      return NextResponse.json({ error: 'Message not found' }, { status: 404 });
    }

    // Allow deletion by author or moderator (for now, allow all — add moderator check later)
    const msg = messages[msgIdx];
    if (deviceId && msg.device_id !== deviceId) {
      // Not the author — could be moderator, allow for now
    }

    messages.splice(msgIdx, 1);
    fs.writeFileSync(filePath, JSON.stringify(messages, null, 2), 'utf-8');
    cache.delete('chat_messages');

    return NextResponse.json({ status: 'ok' });
  } catch (err) {
    console.error('[CHAT] Delete error:', err);
    return NextResponse.json({ error: 'Помилка видалення' }, { status: 500 });
  }
}
