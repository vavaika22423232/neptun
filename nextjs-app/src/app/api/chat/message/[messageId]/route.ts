import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';
import { broadcastSSE } from '../../stream/route';

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

    const msgIdx = messages.findIndex((m) => m.id === messageId);
    if (msgIdx === -1) {
      return NextResponse.json({ error: 'Message not found' }, { status: 404 });
    }

    // Check moderator status
    const modFile = path.join(DATA_DIR, 'chat_moderators.json');
    let isMod = false;
    try {
      if (fs.existsSync(modFile)) {
        const mods = JSON.parse(fs.readFileSync(modFile, 'utf-8'));
        if (Array.isArray(mods) && mods.includes(deviceId)) {
          isMod = true;
        }
      }
    } catch { /* ignore */ }

    const msg = messages[msgIdx];
    const isAuthor = msg.deviceId === deviceId || msg.device_id === deviceId;
    if (!isAuthor && !isMod) {
      return NextResponse.json({ error: 'Недостатньо прав' }, { status: 403 });
    }

    messages.splice(msgIdx, 1);
    fs.writeFileSync(filePath, JSON.stringify(messages, null, 2), 'utf-8');

    // Broadcast via SSE
    broadcastSSE({ type: 'delete_message', data: { messageId } });

    return NextResponse.json({ status: 'ok' });
  } catch (err) {
    console.error('[CHAT] Delete error:', err);
    return NextResponse.json({ error: 'Помилка видалення' }, { status: 500 });
  }
}
