/** Flutter `heatmapOblastFillColor` / `heatmapMaxCount`. */
export function heatmapMaxCount(counts: Record<string, number>): number {
  let max = 0;
  for (const c of Object.values(counts)) {
    if (c > max) max = c;
  }
  return max;
}

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

function rgbToHex(r: number, g: number, b: number): string {
  const h = (n: number) => Math.round(n).toString(16).padStart(2, '0');
  return `#${h(r)}${h(g)}${h(b)}`;
}

function lerpColor(
  c1: [number, number, number],
  c2: [number, number, number],
  t: number,
): string {
  return rgbToHex(lerp(c1[0], c2[0], t), lerp(c1[1], c2[1], t), lerp(c1[2], c2[2], t));
}

/** Returns `#RRGGBB` with alpha applied separately for Leaflet. */
export function heatmapOblastFillColor(
  stateId: string,
  counts: Record<string, number>,
  isDark: boolean,
): { fill: string; fillOpacity: number } {
  const maxCount = heatmapMaxCount(counts);
  const count = counts[stateId] ?? 0;
  if (maxCount <= 0 || count <= 0) {
    return isDark
      ? { fill: '#475569', fillOpacity: 0.14 }
      : { fill: '#CBD5E1', fillOpacity: 0.22 };
  }
  const t = Math.sqrt(count / maxCount);
  const cold: [number, number, number] = [8, 145, 178];
  const warm: [number, number, number] = [251, 191, 36];
  const hot: [number, number, number] = [220, 38, 38];
  const fill =
    t < 0.45
      ? lerpColor(cold, warm, t / 0.45)
      : lerpColor(warm, hot, (t - 0.45) / 0.55);
  const fillOpacity = 0.42 + 0.48 * t;
  return { fill, fillOpacity };
}
