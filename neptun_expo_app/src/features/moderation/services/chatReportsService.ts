import { endpoints } from '../../../config/api';
import { ApiError, apiGet, apiRequest } from '../../../services/apiClient';
import { storage } from '../../../services/storage';
import { parseChatReport, type ChatReport } from '../types';

async function moderatorSecret(): Promise<string | null> {
  return storage.getModeratorSecret();
}

function chatMessagePath(messageId: string): string {
  return `/api/chat/message/${encodeURIComponent(messageId)}`;
}

export const chatReportsService = {
  async loadReports(): Promise<ChatReport[]> {
    const secret = await moderatorSecret();
    if (!secret) {
      throw new Error('Спочатку увійдіть як модератор');
    }

    const data = await apiGet<{ reports?: Record<string, unknown>[] }>(endpoints.adminChatReports, {
      moderatorSecret: secret,
      timeoutMs: 18_000,
    });
    const list = Array.isArray(data.reports) ? data.reports : [];
    return list.map((row) => parseChatReport(row));
  },

  async deleteMessage(messageId: string): Promise<'deleted' | 'missing'> {
    const secret = await moderatorSecret();
    if (!secret) throw new Error('Увійдіть як модератор');

    try {
      await apiRequest(chatMessagePath(messageId), {
        method: 'DELETE',
        moderatorSecret: secret,
        timeoutMs: 18_000,
      });
      return 'deleted';
    } catch (e) {
      if (e instanceof ApiError && e.status === 404) return 'missing';
      throw e;
    }
  },

  async resolveReport(reportId: string, action: 'RESOLVED' | 'REJECTED'): Promise<void> {
    const secret = await moderatorSecret();
    if (!secret) throw new Error('Увійдіть як модератор');

    await apiRequest(endpoints.adminChatReportsResolve, {
      method: 'POST',
      moderatorSecret: secret,
      body: JSON.stringify({ reportId, action }),
      timeoutMs: 18_000,
    });
  },

  async banUser(params: {
    nickname?: string;
    deviceId?: string;
    reason: string;
  }): Promise<void> {
    const secret = await moderatorSecret();
    if (!secret) throw new Error('Увійдіть як модератор');

    await apiRequest(endpoints.adminChatBanUser, {
      method: 'POST',
      moderatorSecret: secret,
      body: JSON.stringify({
        nickname: params.nickname ?? null,
        deviceId: params.deviceId ?? null,
        reason: params.reason,
      }),
      timeoutMs: 18_000,
    });
  },

  async deleteAllUserMessages(params: { nickname?: string; deviceId?: string }): Promise<number> {
    const secret = await moderatorSecret();
    if (!secret) throw new Error('Увійдіть як модератор');

    const data = await apiRequest<{ deleted?: number }>(endpoints.adminChatDeleteUserMessages, {
      method: 'POST',
      moderatorSecret: secret,
      body: JSON.stringify({
        nickname: params.nickname ?? null,
        deviceId: params.deviceId ?? null,
      }),
      timeoutMs: 18_000,
    });
    return Number(data.deleted ?? 0);
  },
};
