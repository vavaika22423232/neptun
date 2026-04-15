import { NextResponse } from 'next/server';
import fs from 'fs';
import fsp from 'fs/promises';
import path from 'path';
import crypto from 'crypto';
import { broadcastSSE } from '@/lib/chat-sse-stream';
import { invalidateChatCache } from '../messages/route';
import { isBanned, isModeratorDevice } from '@/lib/admin/data';
import { requireChatAuth } from '@/lib/chat-auth';

const DATA_DIR = process.env.DATA_DIR || '/data';
const AUDIO_DIR = path.join(DATA_DIR, 'audio');
const CHAT_FILE = path.join(DATA_DIR, 'chat_messages.json');
const FALLBACK_CHAT_FILE = path.resolve(process.cwd(), '..', 'chat_messages.json');

const MAX_MESSAGES = 1000;
const MAX_AUDIO_SIZE = 5 * 1024 * 1024; // 5MB max
const MAX_DURATION = 60; // seconds

// Rate limiter
const rateLimiter = new Map<string, number>();
const RATE_LIMIT_MS = 5000; // 5 seconds for voice

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
 * POST /api/chat/upload-audio
 * Handles multipart form upload of voice messages.
 * Fields: deviceId, nickname, duration
 * File: audio (m4a/mp3/ogg)
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
    const duration = parseInt(formData.get('duration')?.toString() || '0', 10);
    const isPro = formData.get('isPro')?.toString() === 'true';
    const audioFile = formData.get('audio') as File | null;

    if (!audioFile) {
      return NextResponse.json({ error: 'Missing required fields' }, { status: 400 });
    }

    if (duration > MAX_DURATION) {
      return NextResponse.json({ error: 'Audio too long' }, { status: 400 });
    }

    if (audioFile.size > MAX_AUDIO_SIZE) {
      return NextResponse.json({ error: 'File too large' }, { status: 400 });
    }

    // Rate limiting
    const lastSent = rateLimiter.get(deviceId) || 0;
    if (Date.now() - lastSent < RATE_LIMIT_MS) {
      return NextResponse.json({ error: 'Rate limited' }, { status: 429 });
    }
    rateLimiter.set(deviceId, Date.now());

    // Check ban
    if (isBanned(deviceId, nickname, hardwareId)) {
      return NextResponse.json({ error: 'Ви заблоковані' }, { status: 403 });
    }

    // Ensure audio directory exists
    await fsp.mkdir(AUDIO_DIR, { recursive: true });

    // Save audio file
    const ext = audioFile.name?.split('.').pop() || 'm4a';
    const fileName = `voice_${Date.now()}_${crypto.randomBytes(4).toString('hex')}.${ext}`;
    const filePath = path.join(AUDIO_DIR, fileName);

    const buffer = Buffer.from(await audioFile.arrayBuffer());
    await fsp.writeFile(filePath, buffer);

    // Build audio URL
    const audioUrl = `/data/audio/${fileName}`;

    const isModerator = isModeratorDevice(deviceId);

    const now = Date.now() / 1000;
    const nowDate = new Date();

    const message = {
      id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
      userId: nickname,
      deviceId,
      message: '🎤 Голосове повідомлення',
      messageType: 'voice',
      audioUrl,
      audioDuration: duration,
      timestamp: now,
      time: `${nowDate.getHours().toString().padStart(2, '0')}:${nowDate.getMinutes().toString().padStart(2, '0')}`,
      date: `${nowDate.getDate().toString().padStart(2, '0')}.${(nowDate.getMonth() + 1).toString().padStart(2, '0')}.${nowDate.getFullYear()}`,
      isModerator,
      isPro,
      replyTo: null,
      reactions: {},
    };

    // Append to chat file
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

    console.log(`[CHAT] Voice from ${nickname} (${deviceId.slice(0, 8)}…): ${duration}s`);
    return NextResponse.json({ status: 'ok', message });
  } catch (err) {
    console.error('[CHAT] Upload audio error:', err);
    return NextResponse.json({ error: 'Internal error' }, { status: 500 });
  }
}
