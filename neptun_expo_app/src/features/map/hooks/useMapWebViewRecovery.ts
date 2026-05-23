import { useFocusEffect } from '@react-navigation/native';
import { useCallback } from 'react';
import { AppState } from 'react-native';

/**
 * Flutter: `didChangeAppLifecycleState(resumed)` + tab keep-alive recover kicks.
 */
export function useMapWebViewRecovery(onRecover: () => void): void {
  const stableRecover = useCallback(() => {
    onRecover();
  }, [onRecover]);

  useFocusEffect(
    useCallback(() => {
      stableRecover();
      return undefined;
    }, [stableRecover]),
  );

  useFocusEffect(
    useCallback(() => {
      const sub = AppState.addEventListener('change', (state) => {
        if (state === 'active') stableRecover();
      });
      return () => sub.remove();
    }, [stableRecover]),
  );
}
