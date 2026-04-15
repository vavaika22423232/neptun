import { NextResponse } from 'next/server';
import fs from 'fs';
import fsp from 'fs/promises';
import path from 'path';
import crypto from 'crypto';
import { loadChatBans, saveChatBans } from '@/lib/admin/data';
import { requireChatAuth } from '@/lib/chat-auth';

const DATA_DIR = process.env.DATA_DIR || '/data';
const CHAT_FILE = path.join(DATA_DIR, 'chat_messages.json');
const FALLBACK_CHAT_FILE = path.resolve(process.cwd(), '..', 'chat_messages.json');
const VOTES_FILE = path.join(DATA_DIR, 'chat_mute_votes.json');
const FALLBACK_VOTES_FILE = path.resolve(process.cwd(), '..', 'chat_mute_votes.json');

const VOTE_THRESHOLD = 3;
const MUTE_DURATION_MS = 30 * 60 * 1000;

interface MuteVote {
  messageId: string;
  targetDeviceId: string;
  targetNickname: string;
  votes: string[];
  createdAt: string;
}

function resolveVotesFile(): string {
  return fs.existsSync(path.dirname(VOTES_FILE)) ? VOTES_FILE : FALLBACK_VOTES_FILE;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
async function loadMessages(): Promise<any[]> {
  const filePath = fs.existsSync(path.dirname(CHAT_FILE)) ? CHAT_FILE : FALLBACK_CHAT_FILE;
  try {
    const raw = await fsp.readFile(filePath, 'utf-8');
    const data = JSON.parse(raw);
    return Array.isArray(data) ? data : data.messages || [];
  } catch {
    return [];
  }
}

function loadVotes(): MuteVote[] {
  const filePath = resolveVotesFile();
  try {
    if (fs.existsSync(filePath)) {
      const raw = fs.readFileSync(filePath, 'utf-8');
      const data = JSON.parse(raw);
      return Array.isArray(data) ? data : [];
    }
  } catch {
    /* empty */
  }
  return [];
}

async function saveVotes(votes: MuteVote[]): Promise<void> {
  const filePath = resolveVotesFile();
  const dir = path.dirname(filePath);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  const tmp = filePath + '.tmp.' + crypto.randomBytes(4).toString('hex');
  await fsp.writeFile(tmp, JSON.stringify(votes, null, 2), 'utf-8');
  await fsp.rename(tmp, filePath);
}

/**
 * POST /api/chat/vote-mute
 * Crowd-sourced mute: 3 votes → 30-min mute.
 * Body: { messageId } — voter identity from JWT (no spoofing voterDeviceId).
 */
export async function POST(request: Request) {
  try {
    const authResult = requireChatAuth(request);
    if (authResult instanceof Response) return authResult;
    const voterDeviceId = authResult.deviceId;

    const body = await request.json();
    const { messageId } = body;

    if (!messageId || !voterDeviceId) {
      return NextResponse.json({ error: 'Missing messageId' }, { status: 400 });
    }

    const messages = await loadMessages();
    const original = messages.find((m) => m.id === messageId);
    if (!original) {
      return NextResponse.json({ error: 'Повідомлення не знайдено' }, { status: 404 });
    }

    const targetDeviceId = original.deviceId || original.device_id || '';
    const targetNickname = original.userId || original.nickname || 'Анонім';

    if (!targetDeviceId) {
      return NextResponse.json({ error: 'Не можна замьютити цього користувача' }, { status: 400 });
    }

    if (voterDeviceId === targetDeviceId) {
      return NextResponse.json({ error: 'Не можна голосувати за мут власного повідомлення' }, { status: 400 });
    }

    let votes = loadVotes();
    let record = votes.find((v) => v.messageId === messageId);

    if (!record) {
      record = {
        messageId,
        targetDeviceId,
        targetNickname,
        votes: [],
        createdAt: new Date().toISOString(),
      };
      votes.push(record);
    }

    if (record.votes.includes(voterDeviceId)) {
      return NextResponse.json({
        status: 'ok',
        voted: true,
        votesLeft: VOTE_THRESHOLD - record.votes.length,
        muted: false,
      });
    }

    record.votes.push(voterDeviceId);

    if (record.votes.length >= VOTE_THRESHOLD) {
      const bans = loadChatBans();
      const expiresAt = new Date(Date.now() + MUTE_DURATION_MS).toISOString();
      bans.push({
        device_id: targetDeviceId,
        nickname: targetNickname,
        reason: 'Колективний мут (30 хв) за порушення правил',
        banned_at: new Date().toISOString(),
        banned_by: 'crowd-vote',
        expires_at: expiresAt,
      });
      saveChatBans(bans);

      votes = votes.filter((v) => v.messageId !== messageId);
      await saveVotes(votes);

      console.log(`[CHAT] Crowd-mute: ${targetNickname} (${targetDeviceId.slice(0, 8)}…) for 30 min`);
      return NextResponse.json({
        status: 'ok',
        voted: true,
        muted: true,
        message: 'Користувача замьючено на 30 хвилин',
      });
    }

    await saveVotes(votes);
    return NextResponse.json({
      status: 'ok',
      voted: true,
      votesLeft: VOTE_THRESHOLD - record.votes.length,
      muted: false,
    });
  } catch (err) {
    console.error('[CHAT] Vote-mute error:', err);
    return NextResponse.json({ error: 'Помилка' }, { status: 500 });
  }
}
