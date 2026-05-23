import { NextResponse } from 'next/server';
import { getFeedback, updateFeedback } from '@/lib/feedback-db';
import { FeedbackDeviceActionSchema } from '@/lib/api-schemas';
import { requireDeviceAuthFromJson } from '@/lib/device-auth';

/**
 * POST /api/feedback/[id]/read
 * Mark a ticket as read by owner (JWT must match ticket device_id).
 */
export async function POST(
  request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  try {
    const { id } = await params;
    const body = await request.json();
    const parsed = FeedbackDeviceActionSchema.safeParse(body);
    if (!parsed.success) {
      return NextResponse.json({ error: 'bad_device_id' }, { status: 400 });
    }

    const auth = await requireDeviceAuthFromJson(request, body, 'device_id');
    if (!auth.ok) return auth.response;

    const ticket = await getFeedback(id);
    if (!ticket || ticket.device_id !== auth.deviceId) {
      return NextResponse.json({ error: 'Not found' }, { status: 404 });
    }

    await updateFeedback(id, { last_read_at: new Date().toISOString() });

    return NextResponse.json({ status: 'ok' });
  } catch (err) {
    console.error('[FEEDBACK] Read mark error:', err);
    return NextResponse.json({ error: 'Internal error' }, { status: 500 });
  }
}
