import type { ThreatSeverity } from '../types/radar.types';

export function severityForCategoryKey(key: string): ThreatSeverity {
  const t = key.toLowerCase();
  if (['ballistic', 'raketa', 'missile'].includes(t)) return 'critical';
  if (['shahed', 'drone', 'kab'].includes(t)) return 'high';
  if (t === 'avia') return 'medium';
  return 'low';
}
