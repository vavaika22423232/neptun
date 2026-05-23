import { endpoints } from '../../../config/api';
import { apiGet, apiRequest } from '../../../services/apiClient';
import { storage } from '../../../services/storage';
import { parseFeedbackTicket, type FeedbackTicket } from '../types';

async function moderatorSecret(): Promise<string | null> {
  return storage.getModeratorSecret();
}

export const feedbackModerationService = {
  async loadTickets(status: string = 'all'): Promise<FeedbackTicket[]> {
    const secret = await moderatorSecret();
    if (!secret) {
      throw new Error('Спочатку увійдіть як модератор');
    }

    const statusQuery = status === 'all' ? '' : `&status=${encodeURIComponent(status)}`;
    const data = await apiGet<{ feedback?: Record<string, unknown>[] }>(
      `${endpoints.feedback}?limit=100${statusQuery}`,
      { moderatorSecret: secret, timeoutMs: 18_000 },
    );
    const list = Array.isArray(data.feedback) ? data.feedback : [];
    return list.map((row) => parseFeedbackTicket(row));
  },

  async updateStatus(ticketId: string, status: string): Promise<void> {
    const secret = await moderatorSecret();
    if (!secret) throw new Error('Увійдіть як модератор');

    await apiRequest(`${endpoints.feedback}/${encodeURIComponent(ticketId)}`, {
      method: 'PATCH',
      moderatorSecret: secret,
      body: JSON.stringify({ status }),
      timeoutMs: 18_000,
    });
  },

  async sendReply(ticketId: string, message: string): Promise<void> {
    const secret = await moderatorSecret();
    if (!secret) throw new Error('Увійдіть як модератор');

    await apiRequest(`${endpoints.feedback}/${encodeURIComponent(ticketId)}/respond`, {
      method: 'POST',
      moderatorSecret: secret,
      body: JSON.stringify({ message: message.trim(), author: 'admin' }),
      timeoutMs: 18_000,
    });
  },
};
