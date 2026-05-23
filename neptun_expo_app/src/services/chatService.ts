import { endpoints } from '../config/api';
import type { ChatMessage } from '../types/chat';
import { apiRequest } from './apiClient';
import { authService } from './authService';
import { parseChatMessage } from './chatModel';
import { storage } from './storage';

type MessagesResponse = { messages: ChatMessage[]; online: number };
type UploadAsset = {
  uri: string;
  name: string;
  type: string;
};

async function ensureToken(): Promise<string | null> {
  let token = await authService.getAccessToken();
  if (!token) {
    const nickname = await storage.getNickname();
    await authService.login(nickname);
    token = await authService.getAccessToken();
  }
  return token;
}

async function appendUploadAsset(form: FormData, field: string, asset: UploadAsset): Promise<void> {
  if (/^(blob:|data:|https?:)/i.test(asset.uri)) {
    const blob = await fetch(asset.uri).then((r) => r.blob());
    form.append(field, blob, asset.name);
    return;
  }
  form.append(field, { uri: asset.uri, name: asset.name, type: asset.type } as unknown as Blob);
}

export const chatService = {
  async bootstrap(): Promise<{ deviceId: string; nickname: string | null }> {
    const deviceId = await storage.getDeviceId();
    const nickname = await storage.getNickname();
    if (nickname) void authService.login(nickname);
    return { deviceId, nickname };
  },

  async fetchMessages(): Promise<MessagesResponse> {
    const token = await ensureToken();
    const data = await apiRequest<{ messages?: unknown[]; online?: number }>(endpoints.chatMessages, {
      authToken: token,
    });
    return {
      messages: (data.messages ?? []).map(parseChatMessage),
      online: Number(data.online ?? 0),
    };
  },

  async checkNickname(nickname: string): Promise<{ available: boolean; error?: string }> {
    const token = await ensureToken();
    return apiRequest(endpoints.chatCheckNickname, {
      method: 'POST',
      authToken: token,
      body: JSON.stringify({ nickname }),
    });
  },

  async registerNickname(nickname: string): Promise<{ success: boolean; error?: string }> {
    const deviceId = await storage.getDeviceId();
    const token = await ensureToken();
    const result = await apiRequest<{ success?: boolean; error?: string }>(endpoints.chatRegisterNickname, {
      method: 'POST',
      authToken: token,
      body: JSON.stringify({ nickname, deviceId }),
    });
    if (result.success !== false) {
      await storage.setNickname(nickname);
      void authService.login(nickname);
    }
    return { success: result.success !== false, error: result.error };
  },

  async checkBanStatus(): Promise<{ banned: boolean; reason?: string | null }> {
    const token = await ensureToken();
    return apiRequest(endpoints.chatCheckBan, {
      method: 'POST',
      authToken: token,
      body: JSON.stringify({}),
    });
  },

  async sendMessage(text: string, replyToId?: string | null): Promise<ChatMessage> {
    const [deviceId, nickname] = await Promise.all([storage.getDeviceId(), storage.getNickname()]);
    const token = await ensureToken();
    const data = await apiRequest<unknown>(endpoints.chatSend, {
      method: 'POST',
      authToken: token,
      body: JSON.stringify({ text, message: text, deviceId, nickname, replyToId }),
    });
    return parseChatMessage(data);
  },

  async sendImageMessage(asset: UploadAsset, caption?: string | null): Promise<ChatMessage> {
    const [deviceId, nickname] = await Promise.all([storage.getDeviceId(), storage.getNickname()]);
    const token = await ensureToken();
    const form = new FormData();
    form.append('deviceId', deviceId);
    if (nickname) form.append('nickname', nickname);
    if (caption?.trim()) form.append('message', caption.trim());
    await appendUploadAsset(form, 'image', asset);
    const data = await apiRequest<{ message?: unknown }>(endpoints.chatUploadImage, {
      method: 'POST',
      authToken: token,
      body: form,
      timeoutMs: 30000,
    });
    return parseChatMessage(data.message ?? data);
  },

  async sendVoiceMessage(asset: UploadAsset, duration: number): Promise<ChatMessage> {
    const [deviceId, nickname] = await Promise.all([storage.getDeviceId(), storage.getNickname()]);
    const token = await ensureToken();
    const form = new FormData();
    form.append('deviceId', deviceId);
    if (nickname) form.append('nickname', nickname);
    form.append('duration', String(Math.max(0, Math.min(60, Math.round(duration)))));
    await appendUploadAsset(form, 'audio', asset);
    const data = await apiRequest<{ message?: unknown }>(endpoints.chatUploadAudio, {
      method: 'POST',
      authToken: token,
      body: form,
      timeoutMs: 30000,
    });
    return parseChatMessage(data.message ?? data);
  },

  async fetchMoreMessages(beforeSec: number): Promise<ChatMessage[]> {
    const token = await ensureToken();
    const data = await apiRequest<{ messages?: unknown[] }>(`${endpoints.chatMessages}?before=${beforeSec}`, {
      authToken: token,
    });
    return (data.messages ?? []).map(parseChatMessage);
  },

  async sendTyping(typing: boolean): Promise<void> {
    const [deviceId, nickname] = await Promise.all([storage.getDeviceId(), storage.getNickname()]);
    const token = await ensureToken();
    await apiRequest(endpoints.chatStream.replace('/stream', '/typing'), {
      method: 'POST',
      authToken: token,
      body: JSON.stringify({ deviceId, nickname, typing }),
      timeoutMs: 5000,
    }).catch(() => undefined);
  },

  async react(messageId: string, emoji: string): Promise<void> {
    const [deviceId, nickname] = await Promise.all([storage.getDeviceId(), storage.getNickname()]);
    const token = await ensureToken();
    await apiRequest(endpoints.chatStream.replace('/stream', '/react'), {
      method: 'POST',
      authToken: token,
      body: JSON.stringify({ messageId, emoji, deviceId, nickname }),
    });
  },

  async editMessage(messageId: string, text: string): Promise<ChatMessage | null> {
    const token = await ensureToken();
    const data = await apiRequest<unknown>(`/api/chat/message/${messageId}`, {
      method: 'PATCH',
      authToken: token,
      body: JSON.stringify({ text, message: text }),
    });
    return parseChatMessage(data);
  },

  async deleteMessage(messageId: string): Promise<void> {
    const token = await ensureToken();
    await apiRequest(`/api/chat/message/${messageId}`, {
      method: 'DELETE',
      authToken: token,
    });
  },

  async banUser(message: Pick<ChatMessage, 'userId' | 'deviceId'>, reason = 'Порушення правил'): Promise<void> {
    const secret = await storage.getModeratorSecret();
    if (!secret) throw new Error('Увійдіть як модератор');
    await apiRequest(endpoints.chatBanUser, {
      method: 'POST',
      authToken: await ensureToken(),
      moderatorSecret: secret,
      body: JSON.stringify({
        nickname: message.userId,
        targetDeviceId: message.deviceId,
        reason,
      }),
    });
  },

  async deleteAllUserMessages(message: Pick<ChatMessage, 'userId' | 'deviceId'>): Promise<number | null> {
    const secret = await storage.getModeratorSecret();
    if (!secret) return null;
    const data = await apiRequest<{ deleted?: number }>(endpoints.adminChatDeleteUserMessages, {
      method: 'POST',
      moderatorSecret: secret,
      body: JSON.stringify({
        nickname: message.userId,
        deviceId: message.deviceId,
      }),
    });
    return Number(data.deleted ?? 0);
  },

  async getBanList(): Promise<string[]> {
    const secret = await storage.getModeratorSecret();
    if (!secret) return [];
    try {
      const data = await apiRequest<{ details?: { nickname?: string }[]; banned?: string[] }>(
        endpoints.adminChatBanList,
        { moderatorSecret: secret, authToken: await ensureToken() },
      );
      if (Array.isArray(data.details)) {
        return data.details.map((d) => String(d.nickname ?? '')).filter(Boolean);
      }
      if (Array.isArray(data.banned)) return data.banned.map(String);
    } catch {
      return [];
    }
    return [];
  },

  async unbanUser(nickname: string): Promise<boolean> {
    const secret = await storage.getModeratorSecret();
    if (!secret) return false;
    try {
      await apiRequest(endpoints.adminChatUnban, {
        method: 'POST',
        moderatorSecret: secret,
        authToken: await ensureToken(),
        body: JSON.stringify({ nickname }),
      });
      return true;
    } catch {
      return false;
    }
  },

  async reportMessage(messageId: string, reason: string, meta?: Record<string, unknown>): Promise<void> {
    const token = await ensureToken();
    await apiRequest(endpoints.chatReport, {
      method: 'POST',
      authToken: token,
      body: JSON.stringify({ messageId, reason, ...meta }),
    });
  },
};
