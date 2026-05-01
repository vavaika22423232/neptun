'use client';

import { useEffect, useRef, useState } from 'react';

export type ThreatWebSocketStatus = 'idle' | 'connecting' | 'connected' | 'reconnecting' | 'offline';

export type RealtimeThreatEntity = {
  id: string;
  lat: number;
  lng: number;
  threat_type: string;
  bearing?: number | null;
  updated_at?: number;
};

export type RealtimeThreatEvent =
  | { type: 'add'; entity: RealtimeThreatEntity }
  | { type: 'update'; entity: RealtimeThreatEntity }
  | { type: 'remove'; id: string }
  | { type: 'hello'; channel: string };

function defaultWsUrl(path: string): string {
  const configured = process.env.NEXT_PUBLIC_THREAT_WS_URL;
  if (configured) return configured;
  if (typeof window === 'undefined') return '';
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = process.env.NEXT_PUBLIC_THREAT_WS_HOST || window.location.host;
  return `${proto}//${host}${path}`;
}

export function useThreatWebSocket(onEvent?: (event: RealtimeThreatEvent) => void) {
  const [status, setStatus] = useState<ThreatWebSocketStatus>('idle');
  const reconnectRef = useRef<number | null>(null);
  const onEventRef = useRef(onEvent);

  useEffect(() => {
    onEventRef.current = onEvent;
  }, [onEvent]);

  useEffect(() => {
    let closed = false;
    let attempts = 0;
    const url = defaultWsUrl('/ws/threats');
    if (!url) return undefined;

    const connect = () => {
      if (closed) return;
      setStatus(attempts === 0 ? 'connecting' : 'reconnecting');
      const ws = new WebSocket(url);
      ws.onopen = () => {
        attempts = 0;
        setStatus('connected');
      };
      ws.onclose = () => {
        setStatus('offline');
        if (closed) return;
        const delay = Math.min(10_000, 500 * 2 ** attempts);
        attempts += 1;
        reconnectRef.current = window.setTimeout(connect, delay);
      };
      ws.onerror = () => {
        ws.close();
      };
      ws.onmessage = (event) => {
        try {
          onEventRef.current?.(JSON.parse(event.data) as RealtimeThreatEvent);
        } catch {
          /* ignore malformed realtime events */
        }
      };
    };

    connect();
    return () => {
      closed = true;
      if (reconnectRef.current != null) window.clearTimeout(reconnectRef.current);
    };
  }, []);

  return status;
}

export function useSocialMapSocket(enabled: boolean) {
  const [status, setStatus] = useState<ThreatWebSocketStatus>('idle');
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!enabled) {
      wsRef.current?.close();
      wsRef.current = null;
      return undefined;
    }

    let closed = false;
    const url = defaultWsUrl('/ws/social');
    if (!url) return undefined;

    const ws = new WebSocket(url);
    wsRef.current = ws;
    ws.onopen = () => setStatus('connected');
    ws.onclose = () => {
      if (!closed) setStatus('offline');
    };
    ws.onerror = () => ws.close();

    return () => {
      closed = true;
      ws.close();
      wsRef.current = null;
    };
  }, [enabled]);

  return {
    status,
    sendCursor(lat: number, lng: number) {
      const ws = wsRef.current;
      if (!ws || ws.readyState !== WebSocket.OPEN) return;
      const id = localStorage.getItem('neptun_uid') || 'anonymous';
      ws.send(JSON.stringify({ type: 'cursor', id, lat, lng }));
    },
  };
}
