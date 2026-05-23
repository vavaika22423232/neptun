/** Mirrors Flutter `_resolveThreatKey`. */
export function resolveThreatKey(body: string, threatType: string): string {
  const text = `${body} ${threatType}`.toLowerCase();
  if (text.includes('балістик') || text.includes('балистик')) return 'ballistic';
  if (text.includes('каб')) return 'kab';
  if (text.includes('ракет') || text.includes('крилат')) return 'rocket';
  if (text.includes('бпла') || text.includes('дрон') || text.includes('шахед')) return 'drones';
  if (text.includes('артилер') || text.includes('обстріл')) return 'artillery';
  if (text.includes('вибух')) return 'explosion';
  return 'air';
}

export function isThreatTypeAllowed(threatKey: string, allowed: string[]): boolean {
  if (allowed.length === 0) return true;
  return allowed.includes(threatKey);
}
