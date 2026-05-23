import type { ChatMessage } from '../types/chat';
import { dataStreamService } from './dataStreamService';
import { parseChatMessage } from './chatModel';

type Payload = {
  type: string;
  data?: unknown;
};

export function applySsePayloadToMessages(prev: ChatMessage[], payload: Payload): ChatMessage[] {
  if (payload.type === 'new_message') {
    const message = parseChatMessage(payload.data);
    if (prev.some((m) => m.id === message.id)) return prev;
    return [...prev, message];
  }
  if (payload.type === 'delete_message') {
    const id = String((payload.data as { id?: unknown } | undefined)?.id ?? '');
    return id ? prev.filter((m) => m.id !== id) : prev;
  }
  if (payload.type === 'edit_message') {
    const message = parseChatMessage(payload.data);
    return prev.map((m) => (m.id === message.id ? message : m));
  }
  if (payload.type === 'reaction') {
    const data = payload.data as { messageId?: string; id?: string; reactions?: ChatMessage['reactions'] } | undefined;
    const id = data?.messageId ?? data?.id;
    if (!id || !data?.reactions) return prev;
    return prev.map((m) => (m.id === id ? { ...m, reactions: data.reactions ?? {} } : m));
  }
  return prev;
}

export async function connectChatSse(
  handlers: { onPayload: (payload: Payload) => void; onError?: () => void },
  options?: { signal?: AbortSignal },
): Promise<void> {
  dataStreamService.connect();
  const off = [
    dataStreamService.on('connected', (data) => handlers.onPayload({ type: 'connected', data })),
    dataStreamService.on('online', (data) => handlers.onPayload({ type: 'online', data })),
    dataStreamService.on('new_message', (data) => handlers.onPayload({ type: 'new_message', data })),
    dataStreamService.on('delete_message', (data) => handlers.onPayload({ type: 'delete_message', data })),
    dataStreamService.on('edit_message', (data) => handlers.onPayload({ type: 'edit_message', data })),
    dataStreamService.on('reaction', (data) => handlers.onPayload({ type: 'reaction', data })),
    dataStreamService.on('typing', (data) => handlers.onPayload({ type: 'typing', data })),
    dataStreamService.onError(() => handlers.onError?.()),
  ];
  options?.signal?.addEventListener('abort', () => off.forEach((fn) => fn()), { once: true });
}
