/**
 * Re-classify obvious aerostat / air-balloon reports that the regex parser tagged as shahed/uav.
 * Worker may later emit `threat_type: air_balloon` directly; this covers legacy + channel wording.
 *
 * Ukrainian uses many cases: «повітряна куля», «повітряну кулю», «повітряної кулі» — `повітря\w*`
 * before `кул…` catches them; RU «воздушный шар» included for cross-posts.
 * Channels often say «Зонд курсом на …» (recon / aerostat balloon) without the word «куля».
 */
const AIR_BALLOON_TEXT_RE =
  /повітря\w*\s+кул(?:я|ю|і|ь)?\b|aerostat|аеростат|аэростат|air\s*balloon|воздушн\w*\s+шар|зонд[\s,]+курсом|метеозонд|аерозонд|sounding\s*balloon/i;

function haystackForThreatText(marker: Record<string, unknown>): string {
  const parts: string[] = [];
  for (const key of ['text', 'title', 'description', 'place', 'region', 'oblast', 'city'] as const) {
    const v = marker[key];
    if (typeof v === 'string' && v.trim()) parts.push(v);
  }
  return parts.join('\n');
}

const RECLASSIFY_FROM = new Set(['shahed', 'drone', 'uav', 'default', '']);

export function normalizeAirBalloonThreatType(marker: Record<string, unknown>): void {
  const tt = String(marker.threat_type ?? '').toLowerCase().trim();
  if (!RECLASSIFY_FROM.has(tt)) return;
  if (!AIR_BALLOON_TEXT_RE.test(haystackForThreatText(marker))) return;
  marker.threat_type = 'air_balloon';
}
