/**
 * Normalize admin feed events so maritime/offshore rows don't show an admin
 * oblast as if it were the region of the water body (plan: split context).
 */

const OFFSHORE_STATUS_RE = /offshore|акватор|maritime|морськ/i;
const MARITIME_PLACE_RE =
  /чорн(е|ого)?\s+мор(е|я)?|чорномор|акватор(ію|ія)?|black\s*sea|^море$/i;

export function isMaritimeFeedContext(
  resolveStatus: unknown,
  place: unknown,
): boolean {
  const rs = typeof resolveStatus === 'string' ? resolveStatus : '';
  const pl = typeof place === 'string' ? place : '';
  if (OFFSHORE_STATUS_RE.test(rs)) return true;
  if (pl && MARITIME_PLACE_RE.test(pl.trim())) return true;
  return false;
}

/**
 * When offshore/maritime: move worker `region` (usually launch/alarm context) to
 * `context_region`; clear `region` so UI doesn't imply the sea belongs to the oblast.
 */
export function normalizeMaritimeFeedEvent(event: Record<string, unknown>): void {
  const place = event.place;
  const rs = event.resolve_status;
  if (!isMaritimeFeedContext(rs, place)) return;

  const region = event.region;
  if (typeof region === 'string' && region.trim()) {
    if (event.context_region == null || String(event.context_region).trim() === '') {
      event.context_region = region.trim();
    }
    event.region = '';
  }
}
