import { NextResponse } from 'next/server';
import fs from 'fs';
import fsp from 'fs/promises';
import path from 'path';
import crypto from 'crypto';
import { broadcastSSE } from '@/lib/chat-sse-stream';
import { invalidateChatCache } from '../messages/route';
import { isBanned, isModeratorDevice } from '@/lib/admin/data';
import { validateImageMagicBytes } from '@/lib/api-schemas';
import { requireChatAuth } from '@/lib/chat-auth';
import { containsForbiddenText } from '@/lib/chat-forbidden';

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

const DATA_DIR = process.env.DATA_DIR || '/data';
const IMAGES_DIR = path.join(DATA_DIR, 'images');
const CHAT_FILE = path.join(DATA_DIR, 'chat_messages.json');
const FALLBACK_CHAT_FILE = path.resolve(process.cwd(), '..', 'chat_messages.json');

const MAX_MESSAGES = 1000;
const MAX_IMAGE_SIZE = 5 * 1024 * 1024; // 5MB
const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/gif'];

const rateLimiter = new Map<string, number>();
const RATE_LIMIT_MS = 3000;

// eslint-disable-next-line @typescript-eslint/no-explicit-any
async function loadMessages(filePath: string): Promise<any[]> {
  try {
    const raw = await fsp.readFile(filePath, 'utf-8');
    const data = JSON.parse(raw);
    return Array.isArray(data) ? data : data.messages || [];
  } catch { return []; }
}

function resolveChatFile(): string {
  return fs.existsSync(path.dirname(CHAT_FILE)) ? CHAT_FILE : FALLBACK_CHAT_FILE;
}

/**
 * POST /api/chat/upload-image
 * Multipart: image, deviceId, nickname, message (optional caption)
 */
export async function POST(request: Request) {
  try {
    const authResult = requireChatAuth(request);
    if (authResult instanceof Response) return authResult;
    const identity = authResult;

    const formData = await request.formData();

    const formDeviceId = formData.get('deviceId')?.toString();
    if (!formDeviceId || formDeviceId !== identity.deviceId) {
      return NextResponse.json({ error: 'Невідповідність пристрою' }, { status: 403 });
    }
    const deviceId = identity.deviceId;
    const nickname = identity.nickname;
    const hardwareId = formData.get('hardwareId')?.toString() || formData.get('hardware_id')?.toString();
    const rawCaption = (formData.get('message') || formData.get('caption'))?.toString()?.trim() || '';
    const caption = escapeHtml(rawCaption).trim();
    const isPro = formData.get('isPro')?.toString() === 'true';
    const imageFile = formData.get('image') as File | null;

    if (!imageFile) {
      return NextResponse.json({ error: 'Missing required fields' }, { status: 400 });
    }

    const isModerator = isModeratorDevice(deviceId);
    if (!isModerator && caption && containsForbiddenText(caption)) {
      return NextResponse.json(
        { error: 'Підпис містить неприйнятну лексику' },
        { status: 400 },
      );
    }

    if (imageFile.size > MAX_IMAGE_SIZE) {
      return NextResponse.json({ error: 'Зображення занадто велике (макс 5 МБ)' }, { status: 400 });
    }

    const mime = imageFile.type?.toLowerCase() || '';
    if (!ALLOWED_TYPES.includes(mime)) {
      return NextResponse.json({ error: 'Непідтримуваний формат (jpeg, png, webp, gif)' }, { status: 400 });
    }

    // Validate magic bytes to prevent disguised file uploads
    const headerBytes = Buffer.from(await imageFile.slice(0, 8).arrayBuffer());
    if (!validateImageMagicBytes(headerBytes, mime)) {
      return NextResponse.json({ error: 'Файл не відповідає заявленому формату' }, { status: 400 });
    }

    const lastSent = rateLimiter.get(deviceId) || 0;
    if (Date.now() - lastSent < RATE_LIMIT_MS) {
      return NextResponse.json({ error: 'Зачекайте перед наступним повідомленням' }, { status: 429 });
    }
    rateLimiter.set(deviceId, Date.now());

    if (isBanned(deviceId, nickname, hardwareId)) {
      return NextResponse.json({ error: 'Ви заблоковані' }, { status: 403 });
    }

    await fsp.mkdir(IMAGES_DIR, { recursive: true });

    const ext = mime.split('/')[1] || 'jpg';
    const fileName = `img_${Date.now()}_${crypto.randomBytes(4).toString('hex')}.${ext}`;
    const filePath = path.join(IMAGES_DIR, fileName);

    const buffer = Buffer.from(await imageFile.arrayBuffer());
    await fsp.writeFile(filePath, buffer);

    const imageUrl = `/data/images/${fileName}`;

    const now = Date.now() / 1000;
    const nowDate = new Date();

    const message = {
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      userId: nickname,
      deviceId,
      message: caption.length > 0 ? caption : '🖼 Фото',
      messageType: 'image',
      imageUrl,
      timestamp: now,
      time: `${nowDate.getHours().toString().padStart(2, '0')}:${nowDate.getMinutes().toString().padStart(2, '0')}`,
      date: `${nowDate.getDate().toString().padStart(2, '0')}.${(nowDate.getMonth() + 1).toString().padStart(2, '0')}.${nowDate.getFullYear()}`,
      isModerator,
      isPro,
      replyTo: null,
      reactions: {},
    };

    const chatFile = resolveChatFile();
    let messages = await loadMessages(chatFile);
    messages.push(message);
    if (messages.length > MAX_MESSAGES) {
      messages = messages.slice(-MAX_MESSAGES);
    }

    const tmp = chatFile + '.tmp.' + crypto.randomBytes(4).toString('hex');
    await fsp.writeFile(tmp, JSON.stringify(messages), 'utf-8');
    await fsp.rename(tmp, chatFile);

    invalidateChatCache();
    broadcastSSE({ type: 'new_message', data: message });

    return NextResponse.json({ status: 'ok', message });
  } catch (err) {
    console.error('[CHAT] Upload image error:', err);
    return NextResponse.json({ error: 'Internal error' }, { status: 500 });
  }
}
