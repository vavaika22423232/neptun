import type { Map as MapLibreMap } from 'maplibre-gl';

const RECOVER_EVENT = 'neptun:map-recover';
const MOBILE_RESIZE_DELAYS_MS = [0, 120, 320, 900] as const;
const HARD_RECOVER_COOLDOWN_MS = 60_000;

type RecoverReason = 'visibility' | 'pageshow' | 'webgl-restored' | 'flutter' | 'manual';

export type MapLifecycleRecoveryOptions = {
  map: MapLibreMap;
  isMobileLike: boolean;
  /** Full remount only after WebGL loss or BFCache — never on focus/resize heuristics. */
  onHardRecover: () => void;
};

function isMapCanvasHealthy(map: MapLibreMap): boolean {
  try {
    const canvas = map.getCanvas();
    if (!canvas || canvas.width < 2 || canvas.height < 2) return false;
    const layers = map.getStyle()?.layers?.length ?? 0;
    if (layers === 0) return false;
    return Boolean(map.isStyleLoaded());
  } catch {
    return false;
  }
}

function safeResize(map: MapLibreMap): void {
  try {
    map.resize();
    map.triggerRepaint();
  } catch {
    /* map may be removed */
  }
}

/**
 * After background / WebView resume: resize + repaint only.
 * Hard remount is rare (WebGL lost, BFCache) to avoid random full map reloads while panning.
 */
export function attachMapLifecycleRecovery(options: MapLifecycleRecoveryOptions): () => void {
  const { map, isMobileLike, onHardRecover } = options;

  let disposed = false;
  let webglLost = false;
  let lastHardRecoverAt = 0;
  let resizeDebounce: number | null = null;
  let hardRecoverTimer: number | null = null;
  const resizeTimers: number[] = [];

  const clearResizeTimers = () => {
    for (const id of resizeTimers) window.clearTimeout(id);
    resizeTimers.length = 0;
  };

  const scheduleResizeKicks = () => {
    clearResizeTimers();
    const delays = isMobileLike ? MOBILE_RESIZE_DELAYS_MS : ([0, 200] as const);
    for (const ms of delays) {
      resizeTimers.push(
        window.setTimeout(() => {
          if (!disposed) safeResize(map);
        }, ms),
      );
    }
  };

  const scheduleResizeOnly = () => {
    if (resizeDebounce) window.clearTimeout(resizeDebounce);
    resizeDebounce = window.setTimeout(() => {
      resizeDebounce = null;
      if (!disposed) scheduleResizeKicks();
    }, 120);
  };

  const tryHardRecover = (why: 'webgl' | 'bfcache') => {
    if (hardRecoverTimer) window.clearTimeout(hardRecoverTimer);
    const delayMs = why === 'bfcache' ? 120 : 900;
    hardRecoverTimer = window.setTimeout(() => {
      hardRecoverTimer = null;
      if (disposed) return;

      const now = Date.now();
      if (now - lastHardRecoverAt < HARD_RECOVER_COOLDOWN_MS) {
        scheduleResizeKicks();
        return;
      }

      const needsRemount =
        why === 'bfcache' || (webglLost && !isMapCanvasHealthy(map));
      webglLost = false;

      if (needsRemount) {
        lastHardRecoverAt = now;
        onHardRecover();
      } else {
        scheduleResizeKicks();
      }
    }, delayMs);
  };

  const runRecover = (reason: RecoverReason, opts?: { fromBfcache?: boolean }) => {
    if (disposed) return;

    if (opts?.fromBfcache) {
      tryHardRecover('bfcache');
      return;
    }

    if (reason === 'webgl-restored' && webglLost) {
      tryHardRecover('webgl');
      return;
    }

    // visibility / flutter / manual — resize only (no setStyle, no remount)
    scheduleResizeOnly();
  };

  const onVisibilityChange = () => {
    if (document.visibilityState === 'visible') runRecover('visibility');
  };

  const onPageShow = (ev: Event) => {
    const persisted = (ev as PageTransitionEvent).persisted === true;
    runRecover('pageshow', { fromBfcache: persisted });
  };

  const onRecoverEvent = () => runRecover('flutter');

  const onWebGlContextLost = (ev: Event) => {
    ev.preventDefault();
    webglLost = true;
  };

  const onWebGlContextRestored = () => {
    runRecover('webgl-restored');
  };

  const canvas = map.getCanvas();
  canvas.addEventListener('webglcontextlost', onWebGlContextLost, false);
  canvas.addEventListener('webglcontextrestored', onWebGlContextRestored, false);

  document.addEventListener('visibilitychange', onVisibilityChange);
  window.addEventListener('pageshow', onPageShow);
  window.addEventListener(RECOVER_EVENT, onRecoverEvent);

  if (typeof window !== 'undefined') {
    const w = window as Window & { __neptunRecoverMap?: () => void };
    w.__neptunRecoverMap = () => runRecover('manual');
  }

  return () => {
    disposed = true;
    if (resizeDebounce) window.clearTimeout(resizeDebounce);
    if (hardRecoverTimer) window.clearTimeout(hardRecoverTimer);
    clearResizeTimers();
    canvas.removeEventListener('webglcontextlost', onWebGlContextLost);
    canvas.removeEventListener('webglcontextrestored', onWebGlContextRestored);
    document.removeEventListener('visibilitychange', onVisibilityChange);
    window.removeEventListener('pageshow', onPageShow);
    window.removeEventListener(RECOVER_EVENT, onRecoverEvent);
    const w = window as Window & { __neptunRecoverMap?: () => void };
    if (w.__neptunRecoverMap) delete w.__neptunRecoverMap;
  };
}

export function dispatchMapRecover(): void {
  if (typeof window === 'undefined') return;
  window.dispatchEvent(new Event(RECOVER_EVENT));
}
