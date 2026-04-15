import { NextResponse } from 'next/server';
import { getFeedback, updateFeedback, getResponses, parseFeedbackRegions } from '@/lib/feedback-db';
import { requireAdminAuth } from '@/lib/admin/apiAuth';
import { sendPushToDevice } from '@/lib/fcm';

const STATUS_LABELS: Record<string, string> = {
  open: 'Відкрито',
  in_progress: 'В роботі',
  resolved: 'Вирішено',
  closed: 'Закрито',
};

/**
 * GET /api/feedback/[id]
 * Get a single feedback ticket with all responses.
 */
export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;

    const ticket = await getFeedback(id);
    if (!ticket) {
      return NextResponse.json({ error: 'Not found' }, { status: 404 });
    }

    const responses = await getResponses(id);

    return NextResponse.json({
      ...ticket,
      regions: parseFeedbackRegions(
        typeof ticket.regions === 'string' ? ticket.regions : undefined,
      ),
      responses,
    });
  } catch (err) {
    console.error('[FEEDBACK] Get error:', err);
    return NextResponse.json({ error: 'Internal error' }, { status: 500 });
  }
}

/**
 * PATCH /api/feedback/[id]
 * Update feedback ticket status (admin only).
 * Body: { status?: 'open'|'in_progress'|'resolved'|'closed' }
 */
export async function PATCH(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  const authErr = await requireAdminAuth();
  if (authErr) return authErr;

  try {
    const { id } = await params;
    const body = await request.json();
    const { status } = body;

    const validStatuses = ['open', 'in_progress', 'resolved', 'closed'];
    if (status && !validStatuses.includes(status)) {
      return NextResponse.json({ error: 'Invalid status' }, { status: 400 });
    }

    const ticket = await getFeedback(id);
    if (!ticket) {
      return NextResponse.json({ error: 'Not found' }, { status: 404 });
    }

    if (status) {
      const oldStatus = ticket.status;
      await updateFeedback(id, { status, updated_at: new Date().toISOString() });

      // Send push notification when status changes
      const deviceId = ticket.device_id;
      if (deviceId && status !== oldStatus) {
        const label = STATUS_LABELS[status] || status;
        sendPushToDevice(
          deviceId,
          '📋 Статус звернення змінено',
          `Ваше звернення: ${label}`,
          {
            type: 'feedback_status',
            feedback_id: id,
            new_status: status,
            click_action: 'FLUTTER_NOTIFICATION_CLICK',
          },
        ).catch(err => console.error('[FEEDBACK] Status push error:', err));
      }
    }

    return NextResponse.json({ status: 'ok' });
  } catch (err) {
    console.error('[FEEDBACK] Update error:', err);
    return NextResponse.json({ error: 'Internal error' }, { status: 500 });
  }
}
