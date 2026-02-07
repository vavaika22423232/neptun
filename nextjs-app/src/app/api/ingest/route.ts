import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

// ── Config ───────────────────────────────────────────────────────────────────
const AUTH_SECRET = process.env.AUTH_SECRET || '';
const DATA_DIR = process.env.DATA_DIR || '/data';
const MESSAGES_FILE = path.join(DATA_DIR, 'messages.json');

const MAX_MESSAGES = 500;
const RETENTION_HOURS = 3;

// ── Helpers ──────────────────────────────────────────────────────────────────

function loadMessages(): Record<string, unknown>[] {
  try {
    if (fs.existsSync(MESSAGES_FILE)) {
      const raw = fs.readFileSync(MESSAGES_FILE, 'utf-8');
      const data = JSON.parse(raw);
      return Array.isArray(data) ? data : [];
    }
  } catch (err) {
    console.warn('[INGEST] Failed to load messages.json:', err);
  }
  return [];
}

function pruneMessages(messages: Record<string, unknown>[]): Record<string, unknown>[] {
  const cutoff = new Date(Date.now() - RETENTION_HOURS * 60 * 60 * 1000).toISOString();

  let result = messages.filter((m) => {
    // Always keep manual markers
    if (m.manual) return true;

    // Check timestamp — drop if older than cutoff
    const ts = (m.ts || m.timestamp || m.date || '') as string;
    if (ts && ts < cutoff) return false;

    return true;
  });

  // Cap at MAX_MESSAGES (keep newest)
  if (result.length > MAX_MESSAGES) {
    result.sort((a, b) => {
      const aTs = (a.ts || a.timestamp || a.date || '') as string;
      const bTs = (b.ts || b.timestamp || b.date || '') as string;
      return bTs.localeCompare(aTs);
    });
    result = result.slice(0, MAX_MESSAGES);
  }

  return result;
}

function saveMessages(messages: Record<string, unknown>[]): void {
  const dir = path.dirname(MESSAGES_FILE);
  if (!fs.existsSync(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
  const tmpFile = MESSAGES_FILE + '.tmp';
  fs.writeFileSync(tmpFile, JSON.stringify(messages, null, 2), 'utf-8');
  fs.renameSync(tmpFile, MESSAGES_FILE);
}

// ── POST handler ─────────────────────────────────────────────────────────────

export async function POST(request: Request) {
  // Auth check
  if (!AUTH_SECRET) {
    return NextResponse.json({ error: 'AUTH_SECRET not configured' }, { status: 500 });
  }

  const authHeader = request.headers.get('X-Auth-Secret');
  if (authHeader !== AUTH_SECRET) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  // Parse body
  let body: { marker?: Record<string, unknown> };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON' }, { status: 400 });
  }

  const marker = body.marker;
  if (!marker || !marker.lat || !marker.lng) {
    return NextResponse.json({ error: 'Missing marker or coordinates' }, { status: 400 });
  }

  // Load → append → prune → save
  const messages = loadMessages();
  messages.push(marker);
  const pruned = pruneMessages(messages);
  saveMessages(pruned);

  console.log(`[INGEST] Saved marker ${marker.id} (${pruned.length} total)`);

  return NextResponse.json({ ok: true, total: pruned.length });
}
