'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import { usePolling } from './useVisibility';
import { ACTIVE_POLLING_INTERVAL, HIDDEN_POLLING_INTERVAL_DESKTOP, MARKERS_CACHE_TTL } from '@/lib/constants';
import type { Marker, BallisticThreat } from '@/types';

const CACHE_KEY = 'neptun_markers_cache';

function getCachedMarkers(): Marker[] | null {
  try {
    const cached = localStorage.getItem(CACHE_KEY);
    if (!cached) return null;
    const { data, timestamp } = JSON.parse(cached);
    if (Date.now() - timestamp < MARKERS_CACHE_TTL && data?.length > 0) {
      return data;
    }
  } catch {
    // ignore
  }
  return null;
}

function setCachedMarkers(data: Marker[]) {
  try {
    if (data?.length > 0) {
      localStorage.setItem(CACHE_KEY, JSON.stringify({ data, timestamp: Date.now() }));
    }
  } catch {
    // ignore
  }
}

export function useMarkers() {
  const [markers, setMarkers] = useState<Marker[]>([]);
  const [ballisticThreat, setBallisticThreat] = useState<BallisticThreat | null>(null);
  const etagRef = useRef<string | null>(null);
  const inFlightRef = useRef(false);

  // Load cached markers on mount
  useEffect(() => {
    const cached = getCachedMarkers();
    if (cached) setMarkers(cached);
  }, []);

  const fetchMarkers = useCallback(async () => {
    if (document.hidden || inFlightRef.current) return;
    inFlightRef.current = true;

    try {
      const headers: Record<string, string> = {};
      if (etagRef.current) {
        headers['If-None-Match'] = etagRef.current;
      }

      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 8000);

      const response = await fetch('/api/data', { headers, signal: controller.signal });
      clearTimeout(timeoutId);

      if (response.status === 304) return;

      if (!response.ok) {
        const cached = getCachedMarkers();
        if (cached) setMarkers(cached);
        return;
      }

      const newETag = response.headers.get('ETag');
      if (newETag) etagRef.current = newETag;

      const data = await response.json();
      const items: Marker[] = data.tracks || data.items || data || [];

      if (Array.isArray(items) && items.length > 0) {
        setCachedMarkers(items);
        setMarkers(items);
      }

      if (data.ballistic_threat) {
        setBallisticThreat(data.ballistic_threat);
      }
    } catch {
      const cached = getCachedMarkers();
      if (cached) setMarkers(cached);
    } finally {
      inFlightRef.current = false;
    }
  }, []);

  usePolling(fetchMarkers, ACTIVE_POLLING_INTERVAL, HIDDEN_POLLING_INTERVAL_DESKTOP);

  return { markers, ballisticThreat, fetchMarkers };
}
