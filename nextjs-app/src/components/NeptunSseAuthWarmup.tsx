'use client';

import { useEffect } from 'react';
import { warmSseAuth } from '@/hooks/useDataSSE';

/** Fetches anonymous SSE credentials as early as layout mount so EventSource connects sooner than map hooks. */
export default function NeptunSseAuthWarmup() {
  useEffect(() => {
    void warmSseAuth();
  }, []);
  return null;
}
