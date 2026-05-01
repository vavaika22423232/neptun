'use client';

import { useEffect, useRef, useCallback, useSyncExternalStore } from 'react';
import type { Alarm } from '@/types';

type AlarmCallback = (alarms: Alarm[]) => void;
type MarkerCallback = (marker: Record<string, unknown>) => void;
type MarkerDeleteCallback = (id: string) => void;
type TrackUpdateCallback = (data: { track_id: string; mode: string; marker: Record<string, unknown> }) => void;
type ChatEventCallback = (type: string, data: Record<string, unknown>) => void;
type AdminFeedCallback = (data: Record<string, unknown>) => void;
export type SseConnectionStatus = 'connecting' | 'connected' | 'reconnecting' | 'offline';

export type SseConnectionSnapshot = {
  status: SseConnectionStatus;
  retryDelayMs: number;
  connectedAt: number | null;
  lastEventAt: number | null;
  messageCount: number;
};

// Global SSE connection shared across all hooks (singleton)
let globalES: EventSource | null = null;
let retryTimer: ReturnType<typeof setTimeout> | null = null;
const alarmListeners = new Set<AlarmCallback>();
const markerListeners = new Set<MarkerCallback>();
const markerDeleteListeners = new Set<MarkerDeleteCallback>();
const trackUpdateListeners = new Set<TrackUpdateCallback>();
const chatListeners = new Set<ChatEventCallback>();
const adminFeedListeners = new Set<AdminFeedCallback>();
const statusListeners = new Set<() => void>();
let refCount = 0;
let retryDelay = 3000;
const MAX_RETRY_DELAY = 30_000;
let statusSnapshot: SseConnectionSnapshot = {
  status: 'offline',
  retryDelayMs: retryDelay,
  connectedAt: null,
  lastEventAt: null,
  messageCount: 0,
};

function setStatusSnapshot(patch: Partial<SseConnectionSnapshot>) {
  statusSnapshot = { ...statusSnapshot, ...patch };
  statusListeners.forEach((listener) => {
    try {
      listener();
    } catch {
      /* ignore */
    }
  });
}

let _sseToken: string | null = null;
/** When false, token came from anonymous map bootstrap — drop on ES error so we re-POST /api/auth/token. */
let _sseTokenFromChat = false;

/** Shared with usePresence — same key and shape (U + 7 chars, length8). */
function getOrCreateSseDeviceId(): string {
  if (typeof window === 'undefined') return '';
  let userId = localStorage.getItem('neptun_uid');
  if (!userId) {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
    userId = 'U';
    for (let i = 0; i < 7; i++) {
      userId += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    localStorage.setItem('neptun_uid', userId);
  }
  return userId;
}

let anonymousTokenInFlight: Promise<void> | null = null;

async function ensureAnonymousSseToken(): Promise<void> {
  if (typeof window === 'undefined') return;
  if (_sseToken) return;
  if (!anonymousTokenInFlight) {
    anonymousTokenInFlight = (async () => {
      try {
        const deviceId = getOrCreateSseDeviceId();
        if (!deviceId || deviceId.length < 8) return;
        const res = await fetch('/api/auth/token', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ deviceId, nickname: 'Анонім' }),
        });
        if (!res.ok) return;
        const data = (await res.json()) as { access_token?: string };
        if (data.access_token) {
          _sseToken = data.access_token;
          _sseTokenFromChat = false;
        }
      } catch {
        /* network / parse — retry on next connect */
      }
    })().finally(() => {
      anonymousTokenInFlight = null;
    });
  }
  await anonymousTokenInFlight;
}

export function setSSEToken(token: string) {
  if (token === _sseToken) return;
  _sseToken = token;
  _sseTokenFromChat = true;
  if (globalES) {
    globalES.close();
    globalES = null;
  }
  void connectGlobalSSE();
}

async function connectGlobalSSE() {
  if (globalES && globalES.readyState !== EventSource.CLOSED) return;

  setStatusSnapshot({ status: 'connecting', retryDelayMs: retryDelay });

  await ensureAnonymousSseToken();

  if (globalES && globalES.readyState !== EventSource.CLOSED) return;

  if (!_sseToken) {
    if (refCount > 0) {
      setStatusSnapshot({ status: 'reconnecting', retryDelayMs: retryDelay });
      if (retryTimer) clearTimeout(retryTimer);
      retryTimer = setTimeout(() => {
        retryTimer = null;
        void connectGlobalSSE();
      }, retryDelay);
      retryDelay = Math.min(retryDelay * 2, MAX_RETRY_DELAY);
    }
    return;
  }

  const url = `/api/chat/stream?token=${encodeURIComponent(_sseToken)}`;
  const es = new EventSource(url);
  globalES = es;

  es.onmessage = (event) => {
    setStatusSnapshot({
      lastEventAt: Date.now(),
      messageCount: statusSnapshot.messageCount + 1,
    });
    try {
      const parsed = JSON.parse(event.data);
      const { type, data } = parsed;

      if (type === 'alarm_update' && Array.isArray(data)) {
        alarmListeners.forEach((cb) => {
          try { cb(data); } catch { /* ignore */ }
        });
      } else if (type === 'marker_new' && data) {
        markerListeners.forEach((cb) => {
          try { cb(data); } catch { /* ignore */ }
        });
      } else if (type === 'markers_refresh' && data) {
        // Bulk ingest / queue replay — same debounced /api/data fetch as marker_new
        markerListeners.forEach((cb) => {
          try { cb(data); } catch { /* ignore */ }
        });
      } else if (type === 'marker_update' && data) {
        // Follow-up position update — treat same as marker_new (triggers refetch)
        markerListeners.forEach((cb) => {
          try { cb(data); } catch { /* ignore */ }
        });
      } else if (type === 'marker_delete' && data?.id) {
        markerDeleteListeners.forEach((cb) => {
          try { cb(String(data.id)); } catch { /* ignore */ }
        });
      } else if (type === 'track_update' && data) {
        trackUpdateListeners.forEach((cb) => {
          try { cb(data as { track_id: string; mode: string; marker: Record<string, unknown> }); } catch { /* ignore */ }
        });
      } else if (type === 'track_batch' && data?.updates) {
        const updates = data.updates as { track_id: string; mode: string; marker: Record<string, unknown> }[];
        for (const u of updates) {
          trackUpdateListeners.forEach((cb) => {
            try { cb(u); } catch { /* ignore */ }
          });
        }
      } else if (type === 'admin_feed' && data) {
        adminFeedListeners.forEach((cb) => {
          try { cb(data as Record<string, unknown>); } catch { /* ignore */ }
        });
      } else if (['connected', 'online', 'new_message', 'delete_message', 'reaction', 'typing'].includes(type)) {
        chatListeners.forEach((cb) => {
          try { cb(type, data); } catch { /* ignore */ }
        });
      }
    } catch { /* ignore */ }
  };

  es.onopen = () => {
    // Reset backoff on successful connection
    retryDelay = 3000;
    setStatusSnapshot({
      status: 'connected',
      retryDelayMs: retryDelay,
      connectedAt: Date.now(),
      lastEventAt: Date.now(),
    });
  };

  es.onerror = () => {
    es.close();
    globalES = null;
    if (!_sseTokenFromChat) _sseToken = null;
    if (refCount > 0) {
      setStatusSnapshot({ status: 'reconnecting', retryDelayMs: retryDelay });
      if (retryTimer) clearTimeout(retryTimer);
      retryTimer = setTimeout(() => {
        retryTimer = null;
        void connectGlobalSSE();
      }, retryDelay);
      retryDelay = Math.min(retryDelay * 2, MAX_RETRY_DELAY);
    }
  };
}

function disconnectGlobalSSE() {
  if (retryTimer) {
    clearTimeout(retryTimer);
    retryTimer = null;
  }
  if (globalES) {
    globalES.close();
    globalES = null;
  }
  setStatusSnapshot({ status: 'offline', connectedAt: null });
}

export function useSSEStatus(): SseConnectionSnapshot {
  return useSyncExternalStore(
    (listener) => {
      statusListeners.add(listener);
      return () => {
        statusListeners.delete(listener);
      };
    },
    () => statusSnapshot,
    () => statusSnapshot,
  );
}

/**
 * Hook to receive real-time alarm updates via SSE.
 */
export function useAlarmSSE(callback: AlarmCallback) {
  const cbRef = useRef(callback);
  cbRef.current = callback;

  const stableCallback = useCallback<AlarmCallback>((data) => {
    cbRef.current(data);
  }, []);

  useEffect(() => {
    alarmListeners.add(stableCallback);
    refCount++;
    void connectGlobalSSE();

    return () => {
      alarmListeners.delete(stableCallback);
      refCount--;
      if (refCount <= 0) {
        refCount = 0;
        disconnectGlobalSSE();
      }
    };
  }, [stableCallback]);
}

/**
 * Hook to receive real-time new marker events via SSE.
 */
export function useMarkerSSE(callback: MarkerCallback) {
  const cbRef = useRef(callback);
  cbRef.current = callback;

  const stableCallback = useCallback<MarkerCallback>((data) => {
    cbRef.current(data);
  }, []);

  useEffect(() => {
    markerListeners.add(stableCallback);
    refCount++;
    void connectGlobalSSE();

    return () => {
      markerListeners.delete(stableCallback);
      refCount--;
      if (refCount <= 0) {
        refCount = 0;
        disconnectGlobalSSE();
      }
    };
  }, [stableCallback]);
}

/**
 * Hook to receive real-time marker delete events via SSE.
 * Immediately removes marker from local state when admin deletes it.
 */
export function useMarkerDeleteSSE(callback: MarkerDeleteCallback) {
  const cbRef = useRef(callback);
  cbRef.current = callback;

  const stableCallback = useCallback<MarkerDeleteCallback>((id) => {
    cbRef.current(id);
  }, []);

  useEffect(() => {
    markerDeleteListeners.add(stableCallback);
    refCount++;
    void connectGlobalSSE();

    return () => {
      markerDeleteListeners.delete(stableCallback);
      refCount--;
      if (refCount <= 0) {
        refCount = 0;
        disconnectGlobalSSE();
      }
    };
  }, [stableCallback]);
}

/**
 * Hook to receive real-time track update events via SSE.
 * Track updates contain delta position data for an existing track.
 */
export function useTrackUpdateSSE(callback: TrackUpdateCallback) {
  const cbRef = useRef(callback);
  cbRef.current = callback;

  const stableCallback = useCallback<TrackUpdateCallback>((data) => {
    cbRef.current(data);
  }, []);

  useEffect(() => {
    trackUpdateListeners.add(stableCallback);
    refCount++;
    void connectGlobalSSE();

    return () => {
      trackUpdateListeners.delete(stableCallback);
      refCount--;
      if (refCount <= 0) {
        refCount = 0;
        disconnectGlobalSSE();
      }
    };
  }, [stableCallback]);
}

/**
 * Hook to receive chat-related SSE events via the global connection.
 * Callback receives (type, data) for: connected, online, new_message,
 * delete_message, reaction, typing.
 */
export function useChatSSE(callback: ChatEventCallback) {
  const cbRef = useRef(callback);
  cbRef.current = callback;

  const stableCallback = useCallback<ChatEventCallback>((type, data) => {
    cbRef.current(type, data);
  }, []);

  useEffect(() => {
    chatListeners.add(stableCallback);
    refCount++;
    void connectGlobalSSE();

    return () => {
      chatListeners.delete(stableCallback);
      refCount--;
      if (refCount <= 0) {
        refCount = 0;
        disconnectGlobalSSE();
      }
    };
  }, [stableCallback]);
}

/**
 * Hook to receive real-time admin feed events via SSE.
 * Each event is a pipeline status update from the worker.
 */
export function useAdminFeedSSE(callback: AdminFeedCallback) {
  const cbRef = useRef(callback);
  cbRef.current = callback;

  const stableCallback = useCallback<AdminFeedCallback>((data) => {
    cbRef.current(data);
  }, []);

  useEffect(() => {
    adminFeedListeners.add(stableCallback);
    refCount++;
    void connectGlobalSSE();

    return () => {
      adminFeedListeners.delete(stableCallback);
      refCount--;
      if (refCount <= 0) {
        refCount = 0;
        disconnectGlobalSSE();
      }
    };
  }, [stableCallback]);
}
