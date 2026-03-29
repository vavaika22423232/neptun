import { NextResponse } from 'next/server';
import { getFeedback, updateFeedback } from '@/lib/feedback-db';

/**
 * POST /api/feedback/[id]/read
 * Mark a ticket as read by user (updates last_read_at).
 * Body: { device_id: string }
 */
export async function POST(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const body = await request.json();
    const { device_id } = body;

    if (!device_id) {
      return NextResponse.json({ error: 'Missing device_id' }, { status: 400 });
    }

    const ticket = await getFeedback(id);
    if (!ticket || ticket.device_id !== device_id) {
      return NextResponse.json({ error: 'Not found' }, { status: 404 });
    }

    await updateFeedback(id, { last_read_at: new Date().toISOString() });

    return NextResponse.json({ status: 'ok' });
  } catch (err) {
    console.error('[FEEDBACK] Read mark error:', err);
    return NextResponse.json({ error: 'Internal error' }, { status: 500 });
  }
}
