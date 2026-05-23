/** Distinct but calm accents — readable on dark chat canvas. */
const ACCENTS = [
  '#5856D6',
  '#007AFF',
  '#34C759',
  '#FF9500',
  '#FF2D55',
  '#AF52DE',
  '#32ADE6',
  '#FFD60A',
  '#64D2FF',
  '#BF5AF2',
] as const;

function hashSeed(seed: string): number {
  let hash = 0;
  for (let i = 0; i < seed.length; i += 1) hash = (hash * 31 + seed.charCodeAt(i)) >>> 0;
  return hash;
}

export function avatarAccent(seed: string): string {
  return ACCENTS[hashSeed(seed) % ACCENTS.length];
}

export function displayInitials(seed: string): string {
  const trimmed = seed.trim();
  if (!trimmed) return '?';
  return trimmed.slice(0, 2).toUpperCase();
}

function parseHex(hex: string): [number, number, number] {
  const n = hex.replace('#', '');
  if (n.length !== 6) return [44, 44, 46];
  const num = parseInt(n, 16);
  return [(num >> 16) & 0xff, (num >> 8) & 0xff, num & 0xff];
}

function toHex(r: number, g: number, b: number): string {
  return `#${((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1)}`;
}

function blendHex(base: string, accent: string, amount: number): string {
  const [br, bg, bb] = parseHex(base);
  const [ar, ag, ab] = parseHex(accent);
  const t = Math.min(1, Math.max(0, amount));
  return toHex(
    Math.round(br + (ar - br) * t),
    Math.round(bg + (ag - bg) * t),
    Math.round(bb + (ab - bb) * t),
  );
}

/** Subtle incoming bubble tint so groups stay readable but distinguishable. */
export function chatPeerBubbleColor(userId: string, isLight: boolean): string {
  const base = isLight ? '#E9E9EB' : '#2C2C2E';
  return blendHex(base, avatarAccent(userId), isLight ? 0.14 : 0.22);
}

export function avatarInitialsColor(_seed: string): string {
  return '#FFFFFF';
}
