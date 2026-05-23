import type { ChatMessage, ReactionInfo, ReplyInfo } from '../types/chat';

function parseTimestamp(value: unknown): number {
  if (typeof value === 'number') return value < 100000000000 ? Math.trunc(value * 1000) : Math.trunc(value);
  if (typeof value === 'string') {
    const n = Number(value);
    if (!Number.isFinite(n)) return 0;
    return n < 100000000000 ? Math.trunc(n * 1000) : Math.trunc(n);
  }
  return Date.now();
}

function parseReply(value: unknown): ReplyInfo | null {
  if (!value) return null;
  if (typeof value === 'string') return { id: value };
  if (typeof value !== 'object') return null;
  const o = value as Record<string, unknown>;
  return {
    id: String(o.id ?? ''),
    nickname: o.nickname == null ? null : String(o.nickname),
    text: o.text == null && o.message == null ? null : String(o.text ?? o.message),
  };
}

function parseReactions(value: unknown): Record<string, ReactionInfo[]> {
  if (!value || typeof value !== 'object') return {};
  const output: Record<string, ReactionInfo[]> = {};
  for (const [emoji, list] of Object.entries(value as Record<string, unknown>)) {
    if (!Array.isArray(list)) continue;
    output[emoji] = list.map((item) => {
      const o = (item && typeof item === 'object' ? item : {}) as Record<string, unknown>;
      return {
        deviceId: String(o.deviceId ?? ''),
        nickname: String(o.nickname ?? ''),
        timestamp: parseTimestamp(o.timestamp),
      };
    });
  }
  return output;
}

export function parseChatMessage(raw: unknown): ChatMessage {
  const o = (raw && typeof raw === 'object' ? raw : {}) as Record<string, unknown>;
  return {
    id: String(o.id ?? `${Date.now()}`),
    userId: String(o.userId ?? o.nickname ?? ''),
    deviceId: String(o.deviceId ?? o.device_id ?? ''),
    message: String(o.message ?? o.text ?? ''),
    timestamp: parseTimestamp(o.timestamp),
    time: o.time == null ? undefined : String(o.time),
    date: o.date == null ? undefined : String(o.date),
    isModerator: o.isModerator === true,
    isPro: o.isPro === true,
    replyTo: parseReply(o.replyTo),
    reactions: parseReactions(o.reactions),
    messageType: String(o.messageType ?? o.message_type ?? o.type ?? 'text'),
    audioUrl: o.audioUrl == null && o.audio_url == null ? null : String(o.audioUrl ?? o.audio_url),
    audioDuration: typeof o.audioDuration === 'number' ? o.audioDuration : undefined,
    imageUrl: o.imageUrl == null && o.image_url == null ? null : String(o.imageUrl ?? o.image_url),
    editedAt: o.editedAt == null ? null : parseTimestamp(o.editedAt),
  };
}
