import { useCallback, useEffect, useRef, useState } from 'react';
import { ballisticAlertService } from '../services/ballisticAlertService';

const ALL_CLEAR_MS = 4000;

/**
 * Subscribes to [ballisticAlertService] and drives threat / all-clear overlay UI.
 */
export function useBallisticMapOverlays() {
  const [threatVisible, setThreatVisible] = useState(false);
  const [allClearVisible, setAllClearVisible] = useState(false);
  const [allClearProgress, setAllClearProgress] = useState(0);
  const [region, setRegion] = useState<string | null>(null);
  const rafRef = useRef<number | null>(null);

  const dismissThreat = useCallback(() => {
    ballisticAlertService.dismissThreat();
    setThreatVisible(false);
  }, []);

  useEffect(() => {
    const offThreat = ballisticAlertService.onThreat((r) => {
      setRegion(r);
      setAllClearVisible(false);
      setAllClearProgress(0);
      setThreatVisible(true);
    });
    const offClear = ballisticAlertService.onAllClear(() => {
      setThreatVisible(false);
      setAllClearVisible(true);
      setAllClearProgress(0);
      const start = Date.now();
      const tick = () => {
        const p = Math.min(1, (Date.now() - start) / ALL_CLEAR_MS);
        setAllClearProgress(p);
        if (p < 1) {
          rafRef.current = requestAnimationFrame(tick);
        } else {
          setAllClearVisible(false);
        }
      };
      if (rafRef.current != null) cancelAnimationFrame(rafRef.current);
      rafRef.current = requestAnimationFrame(tick);
    });
    return () => {
      offThreat();
      offClear();
      if (rafRef.current != null) cancelAnimationFrame(rafRef.current);
    };
  }, []);

  return {
    threatVisible,
    allClearVisible,
    allClearProgress,
    region,
    dismissThreat,
  };
}

/** Sync ballistic state from `/data` API fields (Flutter native_map_page). */
export function applyBallisticFromApi(active: boolean | null | undefined, region?: string | null): void {
  if (active == null) return;
  if (active && !ballisticAlertService.isActive) {
    ballisticAlertService.triggerThreat(region ?? null);
  } else if (!active && ballisticAlertService.isActive) {
    ballisticAlertService.triggerAllClear(region ?? null);
  }
}
