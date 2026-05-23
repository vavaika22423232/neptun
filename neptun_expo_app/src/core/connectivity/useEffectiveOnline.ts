import { useEffect, useState } from 'react';
import { apiReachability } from './apiReachability';
import type { EffectiveOnlineState } from './types';

/**
 * Connectivity without @react-native-community/netinfo (requires native rebuild).
 * Mirrors Flutter `effectiveOnlineProvider` using `/api/health` + fetch error classification.
 */
export function useEffectiveOnline(): EffectiveOnlineState {
  const [state, setState] = useState<EffectiveOnlineState>('online');

  useEffect(() => {
    apiReachability.start();
    const unsub = apiReachability.subscribe((ok, networkFailed) => {
      if (networkFailed) setState('noNetwork');
      else if (!ok) setState('apiUnreachable');
      else setState('online');
    });
    return () => {
      unsub();
      apiReachability.stop();
    };
  }, []);

  return state;
}
