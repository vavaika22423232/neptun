import { loadSettings } from '@/lib/admin/data';
import { recordHasPhantomAvia } from '@/lib/corroboration-public-gate';

/**
 * Align SSE / ingest broadcast gating with build-markers effConf (missing confidence ≠ 100%).
 */
export function effectiveIngestConfidence(marker: Record<string, unknown>, minConf: number): number {
  if (typeof marker.confidence === 'number' && Number.isFinite(marker.confidence)) {
    return Math.min(1, Math.max(0, marker.confidence));
  }
  const c100 = marker.confidence_0_100;
  if (typeof c100 === 'number' && Number.isFinite(c100)) {
    return Math.min(1, Math.max(0, c100 / 100));
  }
  return minConf;
}

export function ingestShouldBroadcastMarker(marker: Record<string, unknown>, minConf: number): boolean {
  if (Boolean(marker.manual)) return true;
  const s = loadSettings();
  if (
    (s.dualSourceMapGate === true || recordHasPhantomAvia(marker)) &&
    marker.corroboration_pending === true
  ) {
    return false;
  }
  if (marker.hidden === true) return false;
  return effectiveIngestConfidence(marker, minConf) >= minConf;
}
