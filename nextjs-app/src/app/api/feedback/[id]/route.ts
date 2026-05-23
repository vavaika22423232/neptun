import { NextResponse } from 'next/server';
import { getFeedback, updateFeedback, getResponses, parseFeedbackRegions } from '@/lib/feedback-db';
import { requireAdminAuth } from '@/lib/admin/apiAuth';
import { requireDeviceAuth } from '@/lib/device-auth';
import { sendPushToDevice } from '@/lib/fcm';
import { logSecurityEvent } from '@/lib/security-log';

const STATUS_LABELS: Record<string, string> = {
  open: 'Відкрито',
  in_progress: 'В роботі',
  resolved: 'Вирішено',
  closed: 'Закрито',
};

/**
 * GET /api/feedback/[id]
 * Owner (JWT + device_id) or admin only.
 */
export async function GET(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;

    const ticket = await getFeedback(id);
    if (!ticket) {
      return NextResponse.json({ error: 'Not found' }, { status: 404 });
    }

    const adminResult = await requireAdminAuth();
    const isAdmin = adminResult === null;

    if (!isAdmin) {
      if (!ticket.device_id) {
        logSecurityEvent('feedback_access_denied', { reason: 'anonymous_ticket' });
        return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
      }
      const auth = requireDeviceAuth(request, ticket.device_id);
      if (!auth.ok) return auth.response;
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
