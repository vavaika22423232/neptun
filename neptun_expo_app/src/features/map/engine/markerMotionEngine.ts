/**
 * Interpolates marker positions between SSE `track_update` frames.
 * Used for native MapLibre path only — embed map motion stays in Next.js.
 */

export type MotionCoord = { lat: number; lng: number };

export type MotionTarget = {
  key: string;
  from: MotionCoord;
  to: MotionCoord;
  bearing?: number;
  startedAt: number;
  durationMs: number;
};

const DEFAULT_DURATION_MS = 480;
const MAX_ACTIVE = 512;

export class MarkerMotionEngine {
  private readonly active = new Map<string, MotionTarget>();
  private readonly listeners = new Set<(positions: Map<string, MotionCoord>) => void>();
  private raf: number | null = null;

  schedule(
    key: string,
    from: MotionCoord,
    to: MotionCoord,
    bearing?: number,
    durationMs = DEFAULT_DURATION_MS,
  ): void {
    if (from.lat === to.lat && from.lng === to.lng) return;

    if (this.active.size >= MAX_ACTIVE && !this.active.has(key)) {
      const oldest = this.active.keys().next().value;
      if (oldest) this.active.delete(oldest);
    }

    this.active.set(key, {
      key,
      from,
      to,
      bearing,
      startedAt: performance.now(),
      durationMs: Math.max(120, durationMs),
    });
    this.ensureTicking();
  }

  subscribe(listener: (positions: Map<string, MotionCoord>) => void): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  cancel(key: string): void {
    this.active.delete(key);
  }

  clear(): void {
    this.active.clear();
    if (this.raf != null) {
      cancelAnimationFrame(this.raf);
      this.raf = null;
    }
  }

  private ensureTicking(): void {
    if (this.raf != null) return;
    const tick = () => {
      const now = performance.now();
      const out = new Map<string, MotionCoord>();
      for (const [key, motion] of this.active) {
        const t = Math.min(1, (now - motion.startedAt) / motion.durationMs);
        const eased = 1 - (1 - t) ** 3;
        out.set(key, {
          lat: motion.from.lat + (motion.to.lat - motion.from.lat) * eased,
          lng: motion.from.lng + (motion.to.lng - motion.from.lng) * eased,
        });
        if (t >= 1) this.active.delete(key);
      }
      if (out.size > 0) {
        for (const listener of this.listeners) listener(out);
      }
      this.raf = this.active.size > 0 ? requestAnimationFrame(tick) : null;
    };
    this.raf = requestAnimationFrame(tick);
  }
}

export const markerMotionEngine = new MarkerMotionEngine();
