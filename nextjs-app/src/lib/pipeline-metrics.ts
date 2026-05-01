/**
 * Lightweight in-process counters for geo / ingest fixes (per Node worker).
 * For PM2 clusters, each process has its own counts — still useful for spot checks.
 */

let regionMismatchSnaps = 0;
let foreignOriginFixes = 0;

export function bumpRegionMismatchSnap(): void {
  regionMismatchSnaps += 1;
}

export function bumpForeignOriginFix(): void {
  foreignOriginFixes += 1;
}

export function getPipelineMetricsSnapshot(): {
  regionMismatchSnaps: number;
  foreignOriginFixes: number;
} {
  return { regionMismatchSnaps, foreignOriginFixes };
}
