export type RadarQuickFilter =
  | 'all'
  | 'shahedLayer'
  | 'missiles'
  | 'aviation'
  | 'airRaid'
  | 'blasts'
  | 'ppo'
  | 'myRegions'
  | 'highPriority';

export const RADAR_FILTER_ORDER: RadarQuickFilter[] = [
  'all',
  'shahedLayer',
  'missiles',
  'aviation',
  'airRaid',
  'ppo',
  'myRegions',
  'highPriority',
  'blasts',
];

export const RADAR_FILTER_LABELS: Record<RadarQuickFilter, string> = {
  all: 'Усі',
  shahedLayer: 'БПЛА',
  missiles: 'Ракети',
  aviation: 'Авіація',
  airRaid: 'Тривоги',
  blasts: 'Вибухи',
  ppo: 'ППО',
  myRegions: 'Мої області',
  highPriority: 'Висока увага',
};

export function radarFilterMatchesMarker(
  filter: RadarQuickFilter,
  m: Record<string, unknown>,
  myRegions: string[] = [],
): boolean {
  if (filter === 'all') return true;
  const raw = String(m.threatType ?? m.threat_type ?? m.type ?? '')
    .trim()
    .toLowerCase();
  if (!raw && filter !== 'myRegions') return false;

  switch (filter) {
    case 'shahedLayer':
      return ['shahed', 'drone', 'fpv', 'rozved'].includes(raw);
    case 'missiles':
      return ['raketa', 'missile', 'ballistic', 'pusk', 'kab', 'rszv'].includes(raw);
    case 'aviation':
      return raw === 'avia';
    case 'airRaid':
      return raw === 'alarm' || raw === 'alarm_cancel';
    case 'blasts':
      return ['vibuh', 'artillery', 'obstril'].includes(raw);
    case 'ppo':
      return ['pvo', 'ppo', 'air_defense'].includes(raw);
    case 'myRegions': {
      if (!myRegions.length) return false;
      const place = String(m.place ?? m.location ?? '').toLowerCase();
      return myRegions.some((r) => place.includes(r.toLowerCase()));
    }
    case 'highPriority':
      return ['raketa', 'missile', 'ballistic', 'shahed', 'drone', 'kab'].includes(raw);
    default:
      return true;
  }
}
