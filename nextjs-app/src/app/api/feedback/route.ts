import { NextResponse } from 'next/server';
import { z } from 'zod';
import {
  insertFeedback,
  listFeedback,
  getResponses,
  parseFeedbackRegions,
  type FeedbackTicket,
} from '@/lib/feedback-db';
import { requireAdminAuth } from '@/lib/admin/apiAuth';
import { requireDeviceAuth } from '@/lib/device-auth';
import { redisFixedWindowAllow } from '@/lib/redis-rate-limit';
import { getClientIp, ipRedisTag } from '@/lib/client-ip';
import { logSecurityEvent } from '@/lib/security-log';
import { FeedbackPostSchema } from '@/lib/api-schemas';

/**
 * POST /api/feedback
 * Store user feedback from the mobile app.
 */
export async function POST(request: Request) {
  try {
    const ip = getClientIp(request);
    const allowed = await redisFixedWindowAllow(
      `rl:feedback:post:${ipRedisTag(ip)}`,
      8,
      3600,
      false,
    );
    if (!allowed) {
      logSecurityEvent('rate_limit_hit', { route: 'feedback_post' });
      return NextResponse.json({ error: 'Too many requests' }, { status: 429 });
    }

    const rawBody = await request.json();
    const parsed = FeedbackPostSchema.safeParse(rawBody);
    if (!parsed.success) {
      return NextResponse.json(
        { error: parsed.error.issues[0]?.message || 'Invalid input' },
        { status: 400 },
      );
    }

    const { message, type, device_id, device, app_version, regions } = parsed.data;

    if (device_id) {
      const auth = requireDeviceAuth(request, device_id);
      if (!auth.ok) return auth.response;
    }

    const id = `fb_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`;
    const now = new Date().toISOString();

    const ticket: FeedbackTicket = {
      id,
      message,
      type,
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

    console.log(`[FEEDBACK] ${type} ticket created`);
    return NextResponse.json({ status: 'ok', id });
  } catch (err) {
    console.error('[FEEDBACK] Error:', err);
    return NextResponse.json({ error: 'Internal error' }, { status: 500 });
  }
}

/**
 * GET /api/feedback
 * Admin: all tickets (optional status filter).
 * User: only own tickets when device_id matches JWT.
 */
export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const deviceIdParam = searchParams.get('device_id');
    const adminResult = await requireAdminAuth();
    const isAdmin = adminResult === null;

    if (!isAdmin) {
      if (!deviceIdParam) {
        logSecurityEvent('feedback_access_denied', { reason: 'missing_device_id' });
        return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
      }
      const auth = requireDeviceAuth(request, deviceIdParam);
      if (!auth.ok) return auth.response;
    }

    const status = searchParams.get('status') || undefined;
    const limit = Math.min(parseInt(searchParams.get('limit') || '50', 10), 100);

    const scopedDeviceId = isAdmin ? deviceIdParam ?? undefined : deviceIdParam!;

    const { tickets: rows, total } = await listFeedback({
      device_id: scopedDeviceId,
      status,
      limit,
    });

    const tickets = await Promise.all(
      rows.map(async (row) => {
        const responses = await getResponses(row.id);
        return {
          ...row,
          regions: parseFeedbackRegions(
            typeof row.regions === 'string' ? row.regions : undefined,
          ),
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
