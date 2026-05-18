import { NextResponse } from 'next/server';
import { requireAdminAuth } from '@/lib/admin/apiAuth';
import fs from 'fs';
import path from 'path';

export const dynamic = 'force-dynamic';

const DATA_DIR = process.env.DATA_DIR || '/data';
const DB_PATH = path.join(DATA_DIR, 'settlements.db');
const FALLBACK_DB = path.resolve(process.cwd(), '..', 'worker', 'geo', 'data', 'settlements.db');

function getDbPath(): string {
  if (fs.existsSync(DB_PATH)) return DB_PATH;
  if (fs.existsSync(FALLBACK_DB)) return FALLBACK_DB;
  return DB_PATH;
}

/** GET: list recent corrections and stats */
export async function GET() {
  const denied = await requireAdminAuth();
  if (denied) return denied;

  try {
    // We can't use sqlite3 natively in Next.js serverless easily,
    // so we'll read from a JSON corrections file as a bridge.
    const correctionsFile = path.join(DATA_DIR, 'corrections.json');
    const fallbackFile = path.resolve(process.cwd(), '..', 'corrections.json');
    
    let corrections: Array<Record<string, unknown>> = [];
    for (const fp of [correctionsFile, fallbackFile]) {
      try {
        if (fs.existsSync(fp)) {
          corrections = JSON.parse(fs.readFileSync(fp, 'utf-8'));
          break;
        }
      } catch { /* ignore */ }
    }

    return NextResponse.json({
      corrections: corrections.slice(-50).reverse(),
      total: corrections.length,
    });
  } catch (err) {
    console.error('[ADMIN CORRECTIONS GET]', err);
    return NextResponse.json({ error: 'Failed to load corrections' }, { status: 500 });
  }
}

/** POST: submit a new correction */
export async function POST(request: Request) {
  const denied = await requireAdminAuth();
  if (denied) return denied;

  try {
    const body = await request.json();
    const { event_id, place_name, channel, predicted_lat, predicted_lng, predicted_oblast,
            correct_lat, correct_lng, correct_oblast, reason } = body;

    if (!correct_lat || !correct_lng) {
      return NextResponse.json({ error: 'Missing correct coordinates' }, { status: 400 });
    }

    const correction = {
      event_id: event_id || '',
      place_name: place_name || '',
      channel: channel || '',
      predicted_lat: predicted_lat || 0,
      predicted_lng: predicted_lng || 0,
      predicted_oblast: predicted_oblast || '',
      correct_lat: Number(correct_lat),
      correct_lng: Number(correct_lng),
      correct_oblast: correct_oblast || '',
      reason: reason || '',
      created_at: new Date().toISOString(),
    };

    // Save to corrections.json (bridge file for Python worker to read)
    const correctionsFile = path.join(DATA_DIR, 'corrections.json');
    const fallbackFile = path.resolve(process.cwd(), '..', 'corrections.json');
    
    let filePath = correctionsFile;
    let corrections: Array<Record<string, unknown>> = [];

    for (const fp of [correctionsFile, fallbackFile]) {
      try {
        if (fs.existsSync(fp)) {
          corrections = JSON.parse(fs.readFileSync(fp, 'utf-8'));
          filePath = fp;
          break;
        }
      } catch { /* ignore */ }
    }

    // Ensure directory exists
    const dir = path.dirname(filePath);
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }

    corrections.push(correction);
    // Keep last 1000
    if (corrections.length > 1000) {
      corrections = corrections.slice(-1000);
    }

    fs.writeFileSync(filePath, JSON.stringify(corrections, null, 2), 'utf-8');

    return NextResponse.json({ status: 'ok', correction });
  } catch (err) {
    console.error('[ADMIN CORRECTIONS POST]', err);
    return NextResponse.json({ error: 'Failed to save correction' }, { status: 500 });
  }
}
