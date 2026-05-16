import { NextResponse } from 'next/server';
import { broadcastSSE } from '@/lib/chat-sse-stream';
import { appendAdminFeedEntry } from '@/lib/admin-feed-store';
import { verifyIngestOrRespond } from '@/lib/ingest-auth-guard';

export const dynamic = 'force-dynamic';

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return null;
  return value as Record<string, unknown>;
}

export async function POST(request: Request) {
  const denied = await verifyIngestOrRespond(request);
  if (denied) return denied;

  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: 'Invalid JSON' }, { status: 400 });
  }

  const bodyRecord = asRecord(body);
  const event = asRecord(bodyRecord?.event) || bodyRecord;
  if (!event) {
    return NextResponse.json({ error: 'Missing event' }, { status: 400 });
  }

  try {
    const entry = await appendAdminFeedEntry(event);
    broadcastSSE({ type: 'admin_feed', data: entry });
    return NextResponse.json({ ok: true, entry });
  } catch (err) {
    console.warn('[ADMIN-FEED] Redis write error:', err);
    return NextResponse.json({ error: 'Storage error' }, { status: 500 });
  }
}
