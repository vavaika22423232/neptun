'use client';

import { useState, useCallback, useRef } from 'react';
import { usePolling } from './useVisibility';
import { ACTIVE_POLLING_INTERVAL, HIDDEN_POLLING_INTERVAL_DESKTOP } from '@/lib/constants';
import type { FusionTrajectory } from '@/types';

export function useFusionTrajectories() {
  const [trajectories, setTrajectories] = useState<FusionTrajectory[]>([]);
  const inFlightRef = useRef(false);

  const fetchTrajectories = useCallback(async () => {
    if (document.hidden || inFlightRef.current) return;
    inFlightRef.current = true;

    try {
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 8000);

      const response = await fetch('/api/fusion/trajectories', { signal: controller.signal });
      clearTimeout(timeoutId);

      if (!response.ok) return;

      const data = await response.json();
      if (data.status !== 'ok') return;

      setTrajectories(data.trajectories || []);
    } catch {
      // Silently fail - trajectories are supplementary data
    } finally {
      inFlightRef.current = false;
    }
  }, []);

  // Poll at 2x the normal interval (fusion is less critical)
  usePolling(fetchTrajectories, ACTIVE_POLLING_INTERVAL * 2, HIDDEN_POLLING_INTERVAL_DESKTOP * 2);

  return { trajectories, fetchTrajectories };
}
