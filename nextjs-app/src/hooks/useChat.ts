import { useState, useEffect, useCallback, useRef } from 'react';
import type { ChatMessage } from '@/types';
import { useChatSSE, setSSEToken } from './useDataSSE';

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
  voteMute: (messageId: string) => Promise<Response>;
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
        setSSEToken(data.access_token);
        return data.access_token;
      }
    } catch (err) {
      console.error('Failed to fetch chat token', err);
    }
    return null;
  }, [deviceId]);

  const loadMessages = useCallback(async (authToken?: string) => {
    try {
      const t = authToken || token;
      const res = await fetch(`${API}/messages`, {
        headers: t ? { 'Authorization': `Bearer ${t}` } : {},
      });
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
  }, [token]);

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
    fetchToken().then((t) => {
      if (t) loadMessages(t);
      else loadMessages();
    });

    return () => {
      if (typingTimerRef.current) clearTimeout(typingTimerRef.current);
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const ensureToken = useCallback(
    async (nick: string) => {
      let t = token;
      if (!t) {
        t = await fetchToken(nick);
        if (t) setToken(t);
      }
      return t;
    },
    [token, fetchToken],
  );

  // Send message
  const sendMessage = useCallback(
    async (text: string, nickname: string, replyTo?: string): Promise<boolean> => {
      try {
        const authTok = await ensureToken(nickname);
        if (!authTok) {
          setError('Потрібна авторизація');
          return false;
        }

        const post = (t: string) =>
          fetch(`${API}/send`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              Authorization: `Bearer ${t}`,
            },
            body: JSON.stringify({
              message: text,
              replyTo: replyTo || undefined,
            }),
          });

        let res = await post(authTok);
        if (res.status === 401) {
          const fresh = await fetchToken(nickname);
          if (fresh) {
            setToken(fresh);
            res = await post(fresh);
          }
        }

        if (!res.ok) {
          const body = await res.json().catch(() => ({}));
          if (res.status === 429) {
            setError('Зачекайте 3 секунди');
            setTimeout(() => setError(null), 3000);
          } else {
            setError((body as { error?: string }).error || 'Помилка відправки');
          }
          return false;
        }
        return true;
      } catch {
        return false;
      }
    },
    [ensureToken, fetchToken, setError],
  );

  // Delete message
  const deleteMessage = useCallback(
    async (messageId: string): Promise<boolean> => {
      try {
        const nick = localStorage.getItem('neptun_nickname') || 'Анонім';
        const t = await ensureToken(nick);
        if (!t) return false;
        const del = (auth: string) =>
          fetch(`${API}/message/${messageId}`, {
            method: 'DELETE',
            headers: {
              'Content-Type': 'application/json',
              Authorization: `Bearer ${auth}`,
            },
            body: JSON.stringify({ deviceId }),
          });
        let res = await del(t);
        if (res.status === 401) {
          const fresh = await fetchToken(nick);
          if (fresh) {
            setToken(fresh);
            res = await del(fresh);
          }
        }
        return res.ok;
      } catch {
        return false;
      }
    },
    [deviceId, ensureToken, fetchToken],
  );

  // Toggle reaction
  const toggleReaction = useCallback(
    async (messageId: string, emoji: string, nickname: string) => {
      try {
        const t = await ensureToken(nickname);
        if (!t) return;
        const react = (auth: string) =>
          fetch(`${API}/react`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              Authorization: `Bearer ${auth}`,
            },
            body: JSON.stringify({ messageId, emoji }),
          });
        const res = await react(t);
        if (res.status === 401) {
          const fresh = await fetchToken(nickname);
          if (fresh) {
            setToken(fresh);
            await react(fresh);
          }
        }
      } catch {
        /* ignore */
      }
    },
    [ensureToken, fetchToken],
  );

  const sendTyping = useCallback(
    (nickname: string, isTyping: boolean) => {
      void (async () => {
        const t = await ensureToken(nickname);
        if (!t) return;
        fetch(`${API}/typing`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${t}`,
          },
          body: JSON.stringify({ isTyping }),
        }).catch(() => {});
      })();
    },
    [ensureToken],
  );

  const voteMute = useCallback(
    async (messageId: string) => {
      const nick = localStorage.getItem('neptun_nickname') || 'Анонім';
      const t = await ensureToken(nick);
      if (!t) {
        return new Response(JSON.stringify({ error: 'Потрібна авторизація' }), {
          status: 401,
          headers: { 'Content-Type': 'application/json' },
        });
      }
      const post = (auth: string) =>
        fetch(`${API}/vote-mute`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${auth}`,
          },
          body: JSON.stringify({ messageId }),
        });
      let res = await post(t);
      if (res.status === 401) {
        const fresh = await fetchToken(nick);
        if (fresh) {
          setToken(fresh);
          res = await post(fresh);
        }
      }
      return res;
    },
    [ensureToken, fetchToken],
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
          const t = await fetchToken(nickname);
          if (t) setToken(t);
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
    voteMute,
  };
}
