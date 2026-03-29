import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';
import { requireAdminAuth } from '@/lib/admin/apiAuth';
import { broadcastSSE } from '../../stream/route';
import { invalidateChatCache } from '../../messages/route';
import { containsForbiddenText } from '@/lib/chat-forbidden';
import { isModeratorDevice } from '@/lib/admin/data';

const DATA_DIR = process.env.DATA_DIR || '/data';
const CHAT_FILE = path.join(DATA_DIR, 'chat_messages.json');
const FALLBACK_CHAT_FILE = path.resolve(process.cwd(), '..', 'chat_messages.json');
const MAX_MESSAGE_LENGTH = 500;
const EDIT_WINDOW_SEC = 15 * 60; // 15 minutes

function resolveChatFile(): string {
  return fs.existsSync(path.dirname(CHAT_FILE)) ? CHAT_FILE : FALLBACK_CHAT_FILE;
}

import { getJwtSecret } from '@/lib/server-secrets';
import { verifyChatToken } from '@/lib/chat-auth';

/**
 * PATCH /api/chat/message/[messageId]
 * Edit a chat message (author only, within 15 minutes, text only).
 */
export async function PATCH(
  request: Request,
  { params }: { params: Promise<{ messageId: string }> }
) {
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

    const { messageId } = await params;
    const body = await request.json().catch(() => ({}));
    
    // IDENTITY: Exclusively from JWT!
    const deviceId = payload.deviceId;
    const newMessage = (body as Record<string, string>).message?.trim() || '';

    if (!deviceId || !newMessage) {
      return NextResponse.json({ error: 'Missing deviceId or message' }, { status: 400 });
    }
    if (newMessage.length > MAX_MESSAGE_LENGTH) {
      return NextResponse.json({ error: 'Message too long' }, { status: 400 });
    }

    const isModerator = isModeratorDevice(deviceId);
    if (!isModerator && containsForbiddenText(newMessage)) {
      return NextResponse.json(
        { error: 'Повідомлення містить неприйнятну лексику' },
        { status: 400 }
      );
    }

    const filePath = resolveChatFile();
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

    const msgIdx = messages.findIndex((m: { id: string }) => m.id === messageId);
    if (msgIdx === -1) {
      return NextResponse.json({ error: 'Message not found' }, { status: 404 });
    }

    const msg = messages[msgIdx];
    const isAuthor = msg.deviceId === deviceId || msg.device_id === deviceId;
    if (!isAuthor) {
      return NextResponse.json({ error: 'Недостатньо прав' }, { status: 403 });
    }

    // Text messages only (no voice)
    if (msg.messageType === 'voice' || msg.audioUrl) {
      return NextResponse.json({ error: 'Голосові повідомлення не можна редагувати' }, { status: 400 });
    }

    const ts = typeof msg.timestamp === 'number' ? msg.timestamp : parseFloat(msg.timestamp) || 0;
    const ageSec = Date.now() / 1000 - ts;
    if (ageSec > EDIT_WINDOW_SEC) {
      return NextResponse.json(
        { error: 'Час редагування минув (15 хв)' },
        { status: 400 }
      );
    }

    msg.message = newMessage;
    msg.editedAt = Date.now() / 1000;

    fs.writeFileSync(filePath, JSON.stringify(messages, null, 2), 'utf-8');
    invalidateChatCache();
    broadcastSSE({ type: 'edit_message', data: msg });

    return NextResponse.json({ status: 'ok', message: msg });
  } catch (err) {
    console.error('[CHAT] Edit error:', err);
    return NextResponse.json({ error: 'Помилка редагування' }, { status: 500 });
  }
}

/**
 * DELETE /api/chat/message/[messageId]
 * Delete a chat message by ID (moderator or message author).
 */
export async function DELETE(
  request: Request,
  { params }: { params: Promise<{ messageId: string }> }
) {
  try {
    const authHeader = request.headers.get('Authorization') || '';
    const token = authHeader.split(' ')[1];
    const jwtSecret = getJwtSecret();

    let jwtPayload: any = null;
    if (token && jwtSecret) {
      jwtPayload = verifyChatToken(token, jwtSecret);
    }

    const { messageId } = await params;
    const body = await request.json().catch(() => ({}));
    
    // Fallback to body.deviceId ONLY if no valid JWT (Legacy/Moderator tool support)
    // But for common users, the JWT is the primary identity.
    const deviceId = jwtPayload?.deviceId || (body as Record<string, string>).deviceId || '';

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

    // Allow admin auth (X-Auth-Secret or session) to delete any message
    const adminDenied = await requireAdminAuth();
    if (adminDenied) {
      // Not admin — check moderator status by deviceId
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
