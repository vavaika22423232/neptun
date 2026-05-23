import { NextResponse } from 'next/server';
import {
  getFeedback,
  updateFeedback,
  addResponse,
  type FeedbackResponse,
} from '@/lib/feedback-db';
import { requireAdminAuth } from '@/lib/admin/apiAuth';
import { sendPushToDevice } from '@/lib/fcm';
import { FeedbackRespondSchema } from '@/lib/api-schemas';
import { requireDeviceAuthFromJson } from '@/lib/device-auth';

const STATUS_LABELS: Record<string, string> = {
  open: 'Відкрито',
  in_progress: 'В роботі',
  resolved: 'Вирішено',
  closed: 'Закрито',
};

/**
 * POST /api/feedback/[id]/respond
 * Admin: session/secret. User: JWT must match ticket owner; author cannot be spoofed.
 */
export async function POST(
  request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  try {
    const { id } = await params;
    const body = await request.json();
    const parsed = FeedbackRespondSchema.safeParse(body);
    if (!parsed.success) {
      return NextResponse.json({ error: 'Invalid input' }, { status: 400 });
    }

    const { message, author } = parsed.data;

    const ticket = await getFeedback(id);
    if (!ticket) {
      return NextResponse.json({ error: 'Not found' }, { status: 404 });
    }

    const wantsAdmin = author === 'admin';
    if (wantsAdmin) {
      const authErr = await requireAdminAuth();
      if (authErr) return authErr;
    } else {
      const auth = await requireDeviceAuthFromJson(request, body, 'device_id');
      if (!auth.ok) return auth.response;
      if (auth.deviceId !== ticket.device_id) {
        return NextResponse.json({ error: 'Unauthorized' }, { status: 403 });
      }
    }

    const isAdmin = wantsAdmin;
    const responseId = `resp_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`;
    const now = new Date().toISOString();

    const resp: FeedbackResponse = {
      id: responseId,
      feedback_id: id,
      message: message.trim().slice(0, 2000),
      author: isAdmin ? 'admin' : 'user',
      created_at: now,
    };
    await addResponse(resp);

    const newStatus = isAdmin
      ? ticket.status === 'open'
        ? 'in_progress'
        : ticket.status
      : ticket.status === 'resolved' || ticket.status === 'closed'
        ? 'open'
        : ticket.status;
    await updateFeedback(id, { updated_at: now, status: newStatus });

    if (isAdmin && ticket.device_id) {
      const preview = message.trim().slice(0, 100);
      const statusChanged = newStatus !== ticket.status;
      let pushBody = preview;
      if (statusChanged) {
        pushBody = `[${STATUS_LABELS[newStatus] || newStatus}] ${preview}`;
      }
      sendPushToDevice(
        ticket.device_id,
        '💬 Відповідь на звернення',
        pushBody,
        {
          type: 'feedback_reply',
          feedback_id: id,
          new_status: newStatus,
          click_action: 'FLUTTER_NOTIFICATION_CLICK',
        },
      ).catch((err) => console.error('[FEEDBACK] Push error:', err));
    }

    return NextResponse.json({ status: 'ok', response_id: responseId });
  } catch (err) {
    console.error('[FEEDBACK] Response error:', err);
    return NextResponse.json({ error: 'Internal error' }, { status: 500 });
  }
}
