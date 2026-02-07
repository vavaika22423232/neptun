import { NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';

const DATA_DIR = process.env.DATA_DIR || '/data';
const FEEDBACK_FILE = path.join(DATA_DIR, 'feedback.json');

/**
 * POST /api/feedback
 * Store user feedback from the mobile app.
 */
export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { message, type, device_id, device, app_version, regions } = body;

    if (!message) {
      return NextResponse.json({ error: 'Missing message' }, { status: 400 });
    }

    const entry = {
      id: `fb_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
      message,
      type: type || 'general',
      device_id: device_id || '',
      device: device || '',
      app_version: app_version || '',
      regions: regions || [],
      created_at: new Date().toISOString(),
    };

    // Append to feedback file
    let feedback: unknown[] = [];
    try {
      if (fs.existsSync(FEEDBACK_FILE)) {
        feedback = JSON.parse(fs.readFileSync(FEEDBACK_FILE, 'utf-8'));
      }
    } catch { /* empty */ }

    feedback.push(entry);

    // Keep last 500 entries
    if (feedback.length > 500) feedback = feedback.slice(-500);

    const dir = path.dirname(FEEDBACK_FILE);
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
    fs.writeFileSync(FEEDBACK_FILE, JSON.stringify(feedback, null, 2), 'utf-8');

    console.log(`[FEEDBACK] ${type || 'general'} from ${device_id || 'anon'}: ${message.slice(0, 80)}`);
    return NextResponse.json({ status: 'ok' });
  } catch (err) {
    console.error('[FEEDBACK] Error:', err);
    return NextResponse.json({ error: 'Internal error' }, { status: 500 });
  }
}
