import { NextResponse } from 'next/server';
import {
  insertFeedback,
  listFeedback,
  getResponses,
  type FeedbackTicket,
} from '@/lib/feedback-db';
import { requireAdminAuth } from '@/lib/admin/apiAuth';

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

    if (typeof message !== 'string' || message.trim().length < 5) {
      return NextResponse.json({ error: 'Message too short' }, { status: 400 });
    }

    const id = `fb_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`;
    const now = new Date().toISOString();

    const ticket: FeedbackTicket = {
      id,
      message: message.trim().slice(0, 2000),
      type: type || 'general',
      device_id: device_id || '',
      device: device || '',
      app_version: app_version || '',
      regions: JSON.stringify(regions || []),
      status: 'open',
      created_at: now,
      updated_at: now,
      last_read_at: '',
    };

    await insertFeedback(ticket);

    console.log(`[FEEDBACK] ${type || 'general'} from ${device_id || 'anon'} (${device || '?'}): ${message.slice(0, 80)}`);
    return NextResponse.json({ status: 'ok', id });
  } catch (err) {
    console.error('[FEEDBACK] Error:', err);
    return NextResponse.json({ error: 'Internal error' }, { status: 500 });
  }
}

/**
 * GET /api/feedback
 * Read feedback entries. Supports:
 * - Admin (x-auth-secret header): returns all tickets, optionally filtered
 * - User (?device_id=xxx): returns only that user's tickets
 * - ?status=open|in_progress|resolved|closed — filter by status
 * - ?limit=50 — limit results
 */
export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const deviceId = searchParams.get('device_id');
    const adminResult = await requireAdminAuth();
    const isAdmin = adminResult === null;

    const status = searchParams.get('status') || undefined;
    const limit = parseInt(searchParams.get('limit') || '50', 10);

    const { tickets: rows, total } = await listFeedback({
      device_id: (isAdmin || !deviceId) ? undefined : deviceId,
      status,
      limit,
    });

    const tickets = await Promise.all(
      rows.map(async (row) => {
        const responses = await getResponses(row.id);
        return {
          ...row,
          regions: typeof row.regions === 'string' ? JSON.parse(row.regions) : [],
          responses,
          has_unread_response: responses.some(
            (r) =>
              r.author === 'admin' &&
              (!row.last_read_at ||
                new Date(r.created_at) > new Date(row.last_read_at))
          ),
        };
      })
    );

    return NextResponse.json({ feedback: tickets, total });
  } catch (err) {
    console.error('[FEEDBACK] Read error:', err);
    return NextResponse.json({ error: 'Read failed' }, { status: 500 });
  }
}
