import type { Map as MapLibreMap } from 'maplibre-gl';
import type { RefObject } from 'react';

/**
 * Run `fn` when map exists and style is loaded. Retries while the map is still
 * initializing (common on slow mobile / production cold start).
 */
export function scheduleWhenMapReady(
  mapRef: RefObject<MapLibreMap | null>,
  fn: (map: MapLibreMap) => void,
  opts?: { maxWaitMs?: number },
): () => void {
  const maxWaitMs = opts?.maxWaitMs ?? 30_000;
  const started = Date.now();
  let cancelled = false;

  const tryRun = () => {
    if (cancelled) return;

    const map = mapRef.current;
    if (!map) {
      if (Date.now() - started < maxWaitMs) {
        window.setTimeout(tryRun, 50);
      }
      return;
    }

    const execute = () => {
      if (cancelled || !mapRef.current) return;
      fn(mapRef.current);
    };

    if (map.isStyleLoaded()) {
      execute();
      return;
    }

    const onIdle = () => {
      if (cancelled || !mapRef.current) return;
      if (mapRef.current.isStyleLoaded()) execute();
      else mapRef.current.once('idle', onIdle);
    };
    map.once('idle', onIdle);
  };

  tryRun();
  return () => {
    cancelled = true;
  };
}
