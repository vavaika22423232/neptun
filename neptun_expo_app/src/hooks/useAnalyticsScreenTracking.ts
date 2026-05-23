import { usePathname } from 'expo-router';
import { useEffect, useRef } from 'react';
import { analyticsService } from '../services/analyticsService';

/** Logs Expo Router path as Firebase screen view (Flutter automatic screen tracking parity). */
export function useAnalyticsScreenTracking(): void {
  const pathname = usePathname();
  const last = useRef<string | null>(null);

  useEffect(() => {
    if (!pathname || pathname === last.current) return;
    last.current = pathname;
    void analyticsService.logScreenView(pathname);
  }, [pathname]);
}
