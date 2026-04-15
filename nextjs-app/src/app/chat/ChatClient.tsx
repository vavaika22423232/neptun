'use client';

import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { useSearchParams } from 'next/navigation';
import { useChat } from '@/hooks/useChat';
import type { ChatMessage, ReactionInfo } from '@/types';

// ── Device ID (persistent localStorage) ─────────────────────
function getDeviceId(): string {
  if (typeof window === 'undefined') return 'ssr';
  let id = localStorage.getItem('neptun_device_id');
  if (!id) {
    id = `web-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
    localStorage.setItem('neptun_device_id', id);
  }
  return id;
}

// ── Avatar helpers ───────────────────────────────────────────
const AVATAR_COLORS = [
  '#ef5350', '#ec407a', '#ab47bc', '#7e57c2',
  '#5c6bc0', '#42a5f5', '#26c6da', '#26a69a',
  '#66bb6a', '#9ccc65', '#ffca28', '#ffa726',
  '#ff7043', '#8d6e63',
];

function avatarColor(name: string): string {
  let h = 0;
  for (let i = 0; i < name.length; i++) h = name.charCodeAt(i) + ((h << 5) - h);
  return AVATAR_COLORS[Math.abs(h) % AVATAR_COLORS.length];
}

function initials(name: string): string {
  return name
    .split(/\s+/)
    .map((w) => w[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);
}

// ── Reaction emojis ──────────────────────────────────────────
const REACTIONS = ['👍', '❤️', '😂', '😮', '😢', '🔥', '🇺🇦'];

// ── Format timestamp ─────────────────────────────────────────
function fmtTime(ts: number): string {
  const d = new Date(ts * 1000);
  return `${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`;
}

function fmtDate(ts: number): string {
  const d = new Date(ts * 1000);
  const today = new Date();
  if (
    d.getDate() === today.getDate() &&
    d.getMonth() === today.getMonth() &&
    d.getFullYear() === today.getFullYear()
  )
    return 'Сьогодні';
  const yesterday = new Date(today);
  yesterday.setDate(yesterday.getDate() - 1);
  if (
    d.getDate() === yesterday.getDate() &&
    d.getMonth() === yesterday.getMonth() &&
    d.getFullYear() === yesterday.getFullYear()
  )
    return 'Вчора';
  return `${d.getDate().toString().padStart(2, '0')}.${(d.getMonth() + 1).toString().padStart(2, '0')}.${d.getFullYear()}`;
}

// ── Nickname registration modal ──────────────────────────────
function NicknameModal({
  onDone,
  deviceId,
}: {
  onDone: (nick: string) => void;
  deviceId: string;
}) {
  const [nick, setNick] = useState('');
  const [err, setErr] = useState('');
  const [checking, setChecking] = useState(false);

  const submit = async () => {
    const trimmed = nick.trim();
    if (trimmed.length < 2) { setErr('Мінімум 2 символи'); return; }
    if (trimmed.length > 20) { setErr('Максимум 20 символів'); return; }
    setChecking(true);
    setErr('');
    try {
      const check = await fetch('/api/chat/check-nickname', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ nickname: trimmed, deviceId }),
      }).then((r) => r.json());
      if (!check.available) { setErr(check.error || 'Нікнейм зайнятий'); setChecking(false); return; }

      const reg = await fetch('/api/chat/register-nickname', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ nickname: trimmed, deviceId }),
      }).then((r) => r.json());
      
      if (!reg.success) { 
        setErr(reg.error || 'Помилка реєстрації'); 
        setChecking(false); 
        return; 
      }

      // Important: Fetch initial token for this nickname
      await fetch('/api/auth/token', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ deviceId, nickname: trimmed }),
      });

      localStorage.setItem('neptun_nickname', trimmed);
      onDone(trimmed);
    } catch {
      setErr('Помилка мережі');
      setChecking(false);
    }
  };

  return (
    <div className="chat-nickname-overlay">
      <div className="chat-nickname-modal">
        <div className="chat-nickname-icon">💬</div>
        <h2>Введіть нікнейм</h2>
        <p>Ваше ім&apos;я в чаті NEPTUN</p>
        <input
          autoFocus
          maxLength={20}
          value={nick}
          onChange={(e) => setNick(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && submit()}
          placeholder="Нікнейм"
          className="chat-nickname-input"
        />
        {err && <div className="chat-nickname-error">{err}</div>}
        <button onClick={submit} disabled={checking || nick.trim().length < 2} className="chat-nickname-btn">
          {checking ? 'Перевірка...' : 'Увійти в чат'}
        </button>
      </div>
    </div>
  );
}

// ══════════════════════════════════════════════════════════════
// Main Chat component
// ══════════════════════════════════════════════════════════════
export default function ChatClient() {
  const searchParams = useSearchParams();
  const isEmbed = searchParams.get('embed') === '1';
  const [deviceId, setDeviceId] = useState('');
  const [nickname, setNickname] = useState<string | null>(null);
  const [mounted, setMounted] = useState(false);

  // Hydrate device ID and nickname from localStorage
  useEffect(() => {
    setMounted(true);
    const did = getDeviceId();
    setDeviceId(did);
    const savedNick = localStorage.getItem('neptun_nickname');
    if (savedNick) setNickname(savedNick);
  }, []);

  if (!mounted) {
    return <div className="chat-page" style={{ background: 'var(--surface)' }} />;
  }

  if (!nickname) {
    return (
      <div className="chat-page">
        <NicknameModal deviceId={deviceId} onDone={setNickname} />
      </div>
    );
  }

  return <ChatInner deviceId={deviceId} nickname={nickname} isEmbed={isEmbed} />;
}

// ── Chat inner (after nickname is set) ───────────────────────
function ChatInner({
  deviceId,
  nickname,
  isEmbed,
}: {
  deviceId: string;
  nickname: string;
  isEmbed: boolean;
}) {
  const {
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
    voteMute: requestVoteMute,
  } = useChat({ deviceId });

  const [text, setText] = useState('');
  const [replyTo, setReplyTo] = useState<ChatMessage | null>(null);
  const [activeReactionId, setActiveReactionId] = useState<string | null>(null);
  const [showScrollBtn, setShowScrollBtn] = useState(false);

  const listRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const isAtBottomRef = useRef(true);
  const typingTimer = useRef<NodeJS.Timeout | null>(null);

  // Auto-scroll to bottom
  const scrollToBottom = useCallback((smooth = true) => {
    const el = listRef.current;
    if (!el) return;
    el.scrollTo({ top: el.scrollHeight, behavior: smooth ? 'smooth' : 'auto' });
  }, []);

  // Track scroll position
  useEffect(() => {
    const el = listRef.current;
    if (!el) return;
    const onScroll = () => {
      const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
      isAtBottomRef.current = atBottom;
      setShowScrollBtn(!atBottom);
    };
    el.addEventListener('scroll', onScroll, { passive: true });
    return () => el.removeEventListener('scroll', onScroll);
  }, []);

  // Scroll on new messages (if at bottom)
  useEffect(() => {
    if (isAtBottomRef.current) {
      requestAnimationFrame(() => scrollToBottom(false));
    }
  }, [messages, scrollToBottom]);

  // Initial scroll
  useEffect(() => {
    setTimeout(() => scrollToBottom(false), 200);
  }, [scrollToBottom]);

  // In embed mode (WebView), listen to visualViewport resize to handle keyboard
  useEffect(() => {
    if (!isEmbed || typeof window === 'undefined') return;
    const vv = window.visualViewport;
    if (!vv) return;
    const onResize = () => {
      // When keyboard opens, visualViewport height shrinks; scroll input into view
      if (document.activeElement === inputRef.current) {
        requestAnimationFrame(() => {
          inputRef.current?.scrollIntoView?.({ block: 'nearest', behavior: 'smooth' });
        });
      }
    };
    vv.addEventListener('resize', onResize);
    return () => vv.removeEventListener('resize', onResize);
  }, [isEmbed]);

  // Send handler
  const handleSend = async () => {
    const trimmed = text.trim();
    if (!trimmed) return;
    setText('');
    const rid = replyTo?.id;
    setReplyTo(null);
    const ok = await sendMessage(trimmed, nickname, rid);
    if (!ok) setText(trimmed); // restore on failure
    inputRef.current?.focus();
  };

  // Crowd-mute: vote to mute author of a message (3 votes = 30 min mute)
  const voteMute = useCallback(
    async (msg: ChatMessage) => {
      try {
        const res = await requestVoteMute(msg.id);
        const data = await res.json().catch(() => ({}));
        if (res.ok && data.muted) {
          setError('Користувача замьючено на 30 хвилин');
          setTimeout(() => setError(null), 4000);
        } else if (res.ok && data.votesLeft !== undefined) {
          setError(`Проголосовано. Ще ${data.votesLeft} голосів для муту`);
          setTimeout(() => setError(null), 3000);
        } else if (res.status === 401) {
          setError('Увійдіть знову (токен прострочено)');
          setTimeout(() => setError(null), 4000);
        }
      } catch {
        /* ignore */
      }
    },
    [requestVoteMute, setError],
  );

  // Typing indicator
  const onInputChange = (val: string) => {
    setText(val);
    sendTyping(nickname, val.length > 0);
    if (typingTimer.current) clearTimeout(typingTimer.current);
    typingTimer.current = setTimeout(() => sendTyping(nickname, false), 4000);
  };

  // Group messages by date
  const groupedMessages = useMemo(() => {
    const groups: { date: string; messages: ChatMessage[] }[] = [];
    let currentDate = '';
    for (const msg of messages) {
      const d = fmtDate(msg.timestamp);
      if (d !== currentDate) {
        currentDate = d;
        groups.push({ date: d, messages: [] });
      }
      groups[groups.length - 1].messages.push(msg);
    }
    return groups;
  }, [messages]);

  // Filter out self from typing
  const othersTyping = typingUsers.filter((u) => u !== nickname);

  return (
    <div className={`chat-page ${isEmbed ? 'chat-embed' : ''}`}>
      {/* Header */}
      {!isEmbed && (
        <div className="chat-header">
          <div className="chat-header-info">
            <h1>💬 Чат</h1>
            <span className="chat-online">
              <span className="chat-online-dot" /> {online} онлайн
            </span>
          </div>
        </div>
      )}

      {/* Embed compact header */}
      {isEmbed && (
        <div className="chat-header-embed">
          <span className="chat-online">
            <span className="chat-online-dot" /> {online}
          </span>
        </div>
      )}

      {/* Error toast */}
      {error && <div className="chat-toast">{error}</div>}

      {/* Message list */}
      <div className="chat-messages" ref={listRef}>
        {loading && (
          <div className="chat-loading">
            <div className="chat-spinner" />
            <span>Завантаження...</span>
          </div>
        )}

        {!loading && messages.length === 0 && (
          <div className="chat-empty">
            <div className="chat-empty-icon">💬</div>
            <p>Поки що немає повідомлень</p>
            <p className="chat-empty-sub">Будьте першим!</p>
          </div>
        )}

        {groupedMessages.map((group) => (
          <div key={group.date}>
            <div className="chat-date-divider">
              <span>{group.date}</span>
            </div>
            {group.messages.map((msg) => (
              <MessageBubble
                key={msg.id}
                msg={msg}
                isMine={msg.deviceId === deviceId}
                deviceId={deviceId}
                nickname={nickname}
                onReply={() => {
                  setReplyTo(msg);
                  inputRef.current?.focus();
                }}
                onDelete={() => deleteMessage(msg.id)}
                onReact={(emoji) => toggleReaction(msg.id, emoji, nickname)}
                onVoteMute={msg.deviceId !== deviceId ? (m) => voteMute(m) : undefined}
                activeReactionId={activeReactionId}
                setActiveReactionId={setActiveReactionId}
              />
            ))}
          </div>
        ))}

        {/* Typing indicator */}
        {othersTyping.length > 0 && (
          <div className="chat-typing">
            <TypingDots />
            <span>
              {othersTyping.length === 1
                ? `${othersTyping[0]} пише...`
                : `${othersTyping.length} пишуть...`}
            </span>
          </div>
        )}
      </div>

      {/* Scroll to bottom */}
      {showScrollBtn && (
        <button className="chat-scroll-btn" onClick={() => scrollToBottom()}>
          ↓
        </button>
      )}

      {/* Reply preview */}
      {replyTo && (
        <div className="chat-reply-bar">
          <div className="chat-reply-content">
            <span className="chat-reply-name">{replyTo.userId}</span>
            <span className="chat-reply-text">{replyTo.message.slice(0, 80)}</span>
          </div>
          <button className="chat-reply-close" onClick={() => setReplyTo(null)}>✕</button>
        </div>
      )}

      {/* Input */}
      <div className="chat-input-bar">
        <input
          ref={inputRef}
          type="text"
          value={text}
          onChange={(e) => onInputChange(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSend()}
          onFocus={() => {
            if (isEmbed) {
              setTimeout(() => inputRef.current?.scrollIntoView?.({ block: 'nearest', behavior: 'smooth' }), 300);
            }
          }}
          placeholder="Повідомлення..."
          maxLength={500}
          className="chat-input"
        />
        <button
          className="chat-send-btn"
          onClick={handleSend}
          disabled={!text.trim()}
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
            <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z" />
          </svg>
        </button>
      </div>
    </div>
  );
}

// ── Single message bubble ────────────────────────────────────
function MessageBubble({
  msg,
  isMine,
  deviceId,
  nickname,
  onReply,
  onDelete,
  onReact,
  onVoteMute,
  activeReactionId,
  setActiveReactionId,
}: {
  msg: ChatMessage;
  isMine: boolean;
  deviceId: string;
  nickname: string;
  onReply: () => void;
  onDelete: () => void;
  onReact: (emoji: string) => void;
  onVoteMute?: (msg: ChatMessage) => void;
  activeReactionId: string | null;
  setActiveReactionId: (id: string | null) => void;
}) {
  const showPicker = activeReactionId === msg.id;
  const longPressRef = useRef<NodeJS.Timeout | null>(null);
  const bubbleRef = useRef<HTMLDivElement>(null);

  // Close picker on outside click
  useEffect(() => {
    if (!showPicker) return;
    const close = (e: MouseEvent) => {
      if (bubbleRef.current && !bubbleRef.current.contains(e.target as Node)) {
        setActiveReactionId(null);
      }
    };
    document.addEventListener('click', close);
    return () => document.removeEventListener('click', close);
  }, [showPicker, setActiveReactionId]);

  const handleTouchStart = () => {
    longPressRef.current = setTimeout(() => {
      setActiveReactionId(showPicker ? null : msg.id);
    }, 500);
  };

  const handleTouchEnd = () => {
    if (longPressRef.current) clearTimeout(longPressRef.current);
  };

  // System messages
  if (msg.isSystem) {
    return (
      <div className="chat-system-msg">
        <span>{msg.message}</span>
      </div>
    );
  }

  const reactions = msg.reactions || {};
  const hasReactions = Object.keys(reactions).length > 0;

  return (
    <div
      className={`chat-bubble-row ${isMine ? 'mine' : 'other'}`}
      ref={bubbleRef}
      onTouchStart={handleTouchStart}
      onTouchEnd={handleTouchEnd}
      onContextMenu={(e) => {
        e.preventDefault();
        setActiveReactionId(showPicker ? null : msg.id);
      }}
    >
      {/* Avatar */}
      {!isMine && (
        <div className="chat-avatar" style={{ background: avatarColor(msg.userId) }}>
          {initials(msg.userId)}
        </div>
      )}

      <div className={`chat-bubble ${isMine ? 'mine' : 'other'}`}>
        {/* Author + mod badge */}
        {!isMine && (
          <div className="chat-bubble-author">
            {msg.userId}
            {msg.isModerator && <span className="chat-mod-badge">MOD</span>}
            {msg.isPro && <span className="chat-pro-badge">PRO</span>}
          </div>
        )}

        {/* Reply preview */}
        {msg.replyTo && (
          <div className="chat-bubble-reply">
            <span className="chat-bubble-reply-name">{msg.replyTo.userId}</span>
            <span className="chat-bubble-reply-text">
              {msg.replyTo.message.slice(0, 60)}
            </span>
          </div>
        )}

        {/* Text */}
        <div className="chat-bubble-text">{msg.message}</div>

        {/* Time */}
        <div className="chat-bubble-time">{fmtTime(msg.timestamp)}</div>

        {/* Reactions display */}
        {hasReactions && (
          <div className="chat-reactions">
            {Object.entries(reactions).map(([emoji, users]) => {
              const arr = users as ReactionInfo[];
              const myReaction = arr.some((r) => r.deviceId === deviceId);
              return (
                <button
                  key={emoji}
                  className={`chat-reaction-chip ${myReaction ? 'active' : ''}`}
                  onClick={() => onReact(emoji)}
                >
                  {emoji} {arr.length}
                </button>
              );
            })}
          </div>
        )}

        {/* Reaction picker */}
        {showPicker && (
          <div className="chat-reaction-picker">
            {REACTIONS.map((emoji) => (
              <button
                key={emoji}
                className="chat-reaction-pick"
                onClick={() => {
                  onReact(emoji);
                  setActiveReactionId(null);
                }}
              >
                {emoji}
              </button>
            ))}
            <button className="chat-reaction-pick" onClick={onReply}>↩️</button>
            {!isMine && onVoteMute && (
              <button className="chat-reaction-pick chat-mute-pick" onClick={() => onVoteMute(msg)} title="Проголосувати за мут">
                🔇
              </button>
            )}
            {isMine && (
              <button className="chat-reaction-pick chat-delete-pick" onClick={onDelete}>
                🗑️
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Animated typing dots ─────────────────────────────────────
function TypingDots() {
  return (
    <span className="chat-typing-dots">
      <span className="dot" />
      <span className="dot" />
      <span className="dot" />
    </span>
  );
}
