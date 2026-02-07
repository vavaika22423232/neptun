import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

const DATA_DIR = process.env.DATA_DIR || '/data';
const MESSAGES_FILE = path.join(DATA_DIR, 'messages.json');

/**
 * GET /api/messages
 * Returns recent parsed messages for the mobile app's alarm timer widget.
 */
export async function GET() {
  let messages: Record<string, unknown>[] = [];

  try {
    if (fs.existsSync(MESSAGES_FILE)) {
      const raw = fs.readFileSync(MESSAGES_FILE, 'utf-8');
      const data = JSON.parse(raw);
      messages = Array.isArray(data) ? data : [];
    }
  } catch {
    // empty
  }

  // Return last 50 messages, formatted for mobile
  const recent = messages.slice(-50).reverse().map((m) => ({
    location: m.region || m.location || m.place || '',
    text: m.text || '',
    timestamp: m.ts || m.date || m.timestamp || '',
    type: m.threat_type || m.type || '',
  }));

  return NextResponse.json({ messages: recent });
}
