export type ThreatCategory =
  | 'drone'
  | 'missile'
  | 'aviation'
  | 'airAlert'
  | 'airDefense'
  | 'blast'
  | 'official'
  | 'unknown';

export type ThreatSeverity = 'low' | 'medium' | 'high' | 'critical';

export type ThreatSource = 'telegram' | 'official' | 'system' | 'userReport';

export type ThreatTimelineItem = {
  id: string;
  /** Unix ms — для сортування (новіші зверху). */
  at: number | null;
  time: string;
  title: string;
  description?: string;
  source?: ThreatSource;
  severity?: ThreatSeverity;
};

export type ThreatEvent = {
  id: string;
  category: ThreatCategory;
  categoryKey: string;
  title: string;
  locations: string[];
  severity: ThreatSeverity;
  status: 'active' | 'watch' | 'ended';
  createdAt: number | null;
  updatedAt: number | null;
  source: ThreatSource;
  signalCount: number;
  confidence?: number;
  isNew: boolean;
  isFollowed: boolean;
  isMuted: boolean;
  relatedMessages: string[];
  timeline: ThreatTimelineItem[];
  markers: Record<string, unknown>[];
  mapTarget?: { lat: number; lng: number };
};

export type RadarFeedSectionId =
  | 'activeNow'
  | 'newUpdates'
  | 'highAttention'
  | 'nearby'
  | 'official'
  | 'recentlyEnded';

export const RADAR_SECTION_TITLES: Record<RadarFeedSectionId, string> = {
  activeNow: 'Активні зараз',
  newUpdates: 'Нові оновлення',
  highAttention: 'Висока увага',
  nearby: 'Поблизу мене',
  official: 'Офіційні повідомлення',
  recentlyEnded: 'Нещодавно завершені',
};

export type RadarFeedRow =
  | { kind: 'section'; key: string; sectionId: RadarFeedSectionId; title: string }
  | { kind: 'event'; key: string; event: ThreatEvent };

export type ConnectionStatus = 'live' | 'connecting' | 'offline' | 'stale';
