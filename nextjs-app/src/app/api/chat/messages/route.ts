import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

const DATA_DIR = process.env.DATA_DIR || '/data';
const CHAT_FILE = path.join(DATA_DIR, 'chat_messages.json');
const FALLBACK_CHAT_FILE = path.resolve(process.cwd(), '..', 'chat_messages.json');

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function loadChatMessages(): any[] {
  for (const filePath of [CHAT_FILE, FALLBACK_CHAT_FILE]) {
    try {
      if (fs.existsSync(filePath)) {
        const raw = fs.readFileSync(filePath, 'utf-8');
        const data = JSON.parse(raw);
        return Array.isArray(data) ? data : data.messages || [];
      }
    } catch {
      // ignore
    }
  }
  return [];
}

export async function GET() {
  const messages = loadChatMessages();
  const recent = messages.slice(-200);

  // Count unique users from last hour as "online"
  const oneHourAgo = Date.now() / 1000 - 3600;
  const recentUsers = new Set(
    recent
      .filter((m) => {
        const ts = typeof m.timestamp === 'number' ? m.timestamp : Date.now() / 1000;
        return ts > oneHourAgo;
      })
      .map((m: Record<string, unknown>) => m.userId || m.deviceId || m.device_id)
  );

  return NextResponse.json({
    messages: recent,
    online: Math.max(recentUsers.size, 1),
  });
}
