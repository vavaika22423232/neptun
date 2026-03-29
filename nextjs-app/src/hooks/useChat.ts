import { useState, useEffect, useCallback, useRef } from 'react';
import type { ChatMessage } from '@/types';
import { useChatSSE } from './useDataSSE';

const API = '/api/chat';

interface UseChatOptions {
  deviceId: string;
}

interface UseChatReturn {
  messages: ChatMessage[];
  online: number;
  typingUsers: string[];
  loading: boolean;
  error: string | null;
  setError: (msg: string | null) => void;
  sendMessage: (text: string, nickname: string, replyTo?: string) => Promise<boolean>;
  deleteMessage: (messageId: string) => Promise<boolean>;
  toggleReaction: (messageId: string, emoji: string, nickname: string) => Promise<void>;
  sendTyping: (nickname: string, isTyping: boolean) => void;
  registerNickname: (nickname: string) => Promise<{ success: boolean; error?: string }>;
  checkNickname: (nickname: string) => Promise<{ available: boolean; error?: string }>;
}

export function useChat({ deviceId }: UseChatOptions): UseChatReturn {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [online, setOnline] = useState(1);
  const [typingUsers, setTypingUsers] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const typingTimerRef = useRef<NodeJS.Timeout | null>(null);

  // Access token management
  const [token, setToken] = useState<string | null>(null);

  const fetchToken = useCallback(async (nick?: string) => {
    try {
      const savedNick = nick || localStorage.getItem('neptun_nickname') || 'Анонім';
      const res = await fetch('/api/auth/token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ deviceId, nickname: savedNick }),
      });
      if (res.ok) {
        const data = await res.json();
        setToken(data.access_token);
        return data.access_token;
      }
    } catch (err) {
      console.error('Failed to fetch chat token', err);
    }
    return null;
  }, [deviceId]);

  // Load initial messages
  const loadMessages = useCallback(async () => {
    try {
      const res = await fetch(`${API}/messages`);
      if (!res.ok) throw new Error('Failed to load');
      const data = await res.json();
      setMessages(data.messages || []);
      setOnline(data.online || 1);
      setError(null);
    } catch {
      setError('Помилка завантаження');
    } finally {
      setLoading(false);
    }
  }, []);

  // Subscribe to global SSE for chat events
  useChatSSE(useCallback((type: string, data: Record<string, unknown>) => {
    switch (type) {
      case 'connected':
      case 'online':
        setOnline((data.online as number) || 1);
        break;

      case 'new_message':
        setMessages((prev) => {
          const msg = data as unknown as ChatMessage;
          if (prev.some((m) => m.id === msg.id)) return prev;
          const next = [...prev, msg];
          return next.length > 200 ? next.slice(-200) : next;
        });
        break;

      case 'delete_message':
        setMessages((prev) => prev.filter((m) => m.id !== data.messageId));
        break;

      case 'reaction':
        setMessages((prev) =>
          prev.map((m) =>
            m.id === data.messageId ? { ...m, reactions: data.reactions as ChatMessage['reactions'] } : m
          )
        );
        break;

      case 'typing':
        setTypingUsers((data.users as string[]) || []);
        break;
    }
  }, []));

  useEffect(() => {
    loadMessages();
    fetchToken(); // Initial token fetch

    return () => {
      if (typingTimerRef.current) clearTimeout(typingTimerRef.current);
    };
  }, [loadMessages, fetchToken]);

  // Send message
  const sendMessage = useCallback(
    async (text: string, nickname: string, replyTo?: string): Promise<boolean> => {
      try {
        let currentToken = token;
        if (!currentToken) {
          currentToken = await fetchToken(nickname);
        }

        const res = await fetch(`${API}/send`, {
          method: 'POST',
          headers: { 
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${currentToken}`
          },
          body: JSON.stringify({
            deviceId,
            userId: nickname,
            nickname,
            message: text,
            replyTo: replyTo || undefined,
          }),
        });

        if (!res.ok) {
          if (res.status === 401 && !token) {
            // Retry once with a fresh token if 401
            const fresh = await fetchToken(nickname);
            if (fresh) {
               return sendMessage(text, nickname, replyTo);
            }
          }
          const body = await res.json().catch(() => ({}));
          if (res.status === 429) {
            setError('Зачекайте 3 секунди');
            setTimeout(() => setError(null), 3000);
          } else {
            setError(body.error || 'Помилка відправки');
          }
          return false;
        }
        return true;
      } catch {
        return false;
      }
    },
    [deviceId, token, fetchToken, setError]
  );

  // Delete message
  const deleteMessage = useCallback(
    async (messageId: string): Promise<boolean> => {
      try {
        const res = await fetch(`${API}/message/${messageId}`, {
          method: 'DELETE',
          headers: { 
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({ deviceId }),
        });
        return res.ok;
      } catch {
        return false;
      }
    },
    [deviceId, token]
  );

  // Toggle reaction
  const toggleReaction = useCallback(
    async (messageId: string, emoji: string, nickname: string) => {
      try {
        await fetch(`${API}/react`, {
          method: 'POST',
          headers: { 
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({ messageId, emoji, deviceId, nickname }),
        });
      } catch {
        /* ignore */
      }
    },
    [deviceId, token]
  );

  // Typing indicator
  const sendTyping = useCallback(
    (nickname: string, isTyping: boolean) => {
      fetch(`${API}/typing`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ deviceId, nickname, isTyping }),
      }).catch(() => {});
    },
    [deviceId]
  );

  // Register nickname
  const registerNickname = useCallback(
    async (nickname: string) => {
      try {
        const res = await fetch(`${API}/register-nickname`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ nickname, deviceId }),
        });
        const data = await res.json();
        if (data.success) {
          fetchToken(nickname); // Refresh token with new nickname
        }
        return data;
      } catch {
        return { success: false, error: 'Помилка мережі' };
      }
    },
    [deviceId, fetchToken]
  );

  // Check nickname availability
  const checkNickname = useCallback(
    async (nickname: string) => {
      try {
        const res = await fetch(`${API}/check-nickname`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ nickname, deviceId }),
        });
        return await res.json();
      } catch {
        return { available: false, error: 'Помилка перевірки' };
      }
    },
    [deviceId]
  );

  return {
    messages,
    online,
    typingUsers,
    loading,
    error,
    setError,
    sendMessage,
    deleteMessage,
    toggleReaction,
    sendTyping,
    registerNickname,
    checkNickname,
  };
}
