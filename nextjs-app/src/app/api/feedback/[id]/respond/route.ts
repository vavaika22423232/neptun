import { NextResponse } from 'next/server';
import {
  getFeedback,
  updateFeedback,
  addResponse,
  type FeedbackResponse,
} from '@/lib/feedback-db';
import { requireAdminAuth } from '@/lib/admin/apiAuth';
import { sendPushToDevice } from '@/lib/fcm';

const STATUS_LABELS: Record<string, string> = {
  open: 'Відкрито',
  in_progress: 'В роботі',
  resolved: 'Вирішено',
  closed: 'Закрито',
};

/**
 * POST /api/feedback/[id]/respond
 * Add a response to a feedback ticket.
 * Admin: requires auth. User: requires matching device_id.
 * Body: { message: string, author?: 'admin'|'user', device_id?: string }
 */
export async function POST(
  request: Request,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    const body = await request.json();
    const { message, author, device_id } = body;

    if (!message || typeof message !== 'string' || message.trim().length < 1) {
      return NextResponse.json({ error: 'Missing message' }, { status: 400 });
    }

    const ticket = await getFeedback(id);
    if (!ticket) {
      return NextResponse.json({ error: 'Not found' }, { status: 404 });
    }

    const isAdmin = author === 'admin';
    if (isAdmin) {
      // Admin must be authenticated
      const authErr = await requireAdminAuth();
      if (authErr) return authErr;
    } else {
      // User must provide matching device_id
      if (!device_id || device_id !== ticket.device_id) {
        return NextResponse.json({ error: 'Unauthorized' }, { status: 403 });
      }
    }

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

    // Update ticket timestamp and reopen if resolved and user responded
    const newStatus = isAdmin
      ? ticket.status === 'open'
        ? 'in_progress'
        : ticket.status
      : ticket.status === 'resolved' || ticket.status === 'closed'
        ? 'open'
        : ticket.status;
    await updateFeedback(id, { updated_at: now, status: newStatus });

    console.log(`[FEEDBACK] Response to ${id} from ${isAdmin ? 'admin' : 'user'}: ${message.slice(0, 80)}`);

    // Send push notification to user when admin replies
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
      ).catch(err => console.error('[FEEDBACK] Push error:', err));
    }

    return NextResponse.json({ status: 'ok', response_id: responseId });
  } catch (err) {
    console.error('[FEEDBACK] Response error:', err);
    return NextResponse.json({ error: 'Internal error' }, { status: 500 });
  }
}
