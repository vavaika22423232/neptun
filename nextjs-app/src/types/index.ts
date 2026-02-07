// ============================================
// Core domain types for NEPTUN
// ============================================

export interface Marker {
  id?: string;
  lat: number;
  lng: number;
  threat_type: string;
  place?: string;
  text?: string;
  date?: string;
  count?: number;
  marker_icon?: string;
  course_bearing?: number | null;
  course_direction?: string;
  arrow_direction?: string;
  distance_km?: number;
  speed_kmh?: number;
  prediction_confidence?: number;
  confidence_level?: string;
  trajectory?: Trajectory | null;
}

export interface Trajectory {
  start?: [number, number];
  end?: [number, number];
  predicted?: boolean;
}

export interface FusionTrajectory {
  event_id: string;
  threat_type?: string;
  actual_path: [number, number][];
  predicted_path?: [number, number][];
  confidence?: number;
  last_seen?: string;
}

export interface Alarm {
  regionId: string;
  regionType: 'State' | 'District';
  regionName?: string;
  activeAlerts: ActiveAlert[];
}

export interface ActiveAlert {
  type: string;
  lastUpdate?: string;
}

export interface MarkersResponse {
  tracks?: Marker[];
  items?: Marker[];
  ballistic_threat?: BallisticThreat;
  etag?: string;
}

export interface BallisticThreat {
  active: boolean;
  region?: string;
}

export interface PresenceData {
  web?: number;
  apps?: number;
  total?: number;
}

export interface ReactionInfo {
  deviceId: string;
  nickname: string;
  timestamp: number;
}

export interface ReplyInfo {
  id: string;
  userId: string;
  message: string;
}

export interface ChatMessage {
  id: string;
  userId: string;
  deviceId?: string;
  message: string;
  timestamp: number; // epoch seconds
  replyTo?: ReplyInfo | null;
  isModerator?: boolean;
  isSystem?: boolean;
  systemType?: string;
  threatType?: string;
  region?: string;
  reactions?: Record<string, ReactionInfo[]>;
}

export interface FusionResponse {
  status: string;
  trajectories: FusionTrajectory[];
  count?: number;
}

// Map bounds for Ukraine
export const MAP_BOUNDS = {
  minLat: 44.2,
  maxLat: 52.4,
  minLng: 22.0,
  maxLng: 40.2,
} as const;

// Threat type icon mapping (must match original index.html exactly)
export const THREAT_ICONS: Record<string, string> = {
  shahed: 'shahed3.webp',
  drone: 'shahed3.webp',
  uav: 'shahed3.webp',          // parser alias
  raketa: 'icon_balistic.svg',
  missile: 'icon_balistic.svg', // parser alias
  avia: 'avia.png',
  artillery: 'artillery.png',
  obstril: 'icon_obstril.svg',
  fpv: 'fpv.png',
  pusk: 'pusk.png',
  launch: 'pusk.png',           // parser alias
  kab: 'icon_missile.svg',
  rszv: 'icon_missile.svg',
  rozved: 'rozvedka2.png',
  vibuh: 'icon_vibuh.svg',
  explosion: 'icon_vibuh.svg',  // parser alias
  alarm: 'trivoga.png',
  alarm_cancel: 'vidboi.png',
  default: 'shahed3.webp',
};

// Threat type display names (Ukrainian, must match original)
export const THREAT_NAMES: Record<string, string> = {
  shahed: '🛩️ Шахеди/БПЛА',
  drone: '🛩️ Шахеди/БПЛА',
  uav: '🛩️ Шахеди/БПЛА',
  raketa: '🚀 Ракети',
  missile: '🚀 Ракети',
  avia: '✈️ Авіація',
  artillery: '💥 Артилерія',
  obstril: '💥 Обстріл',
  fpv: '🎯 FPV дрони',
  pusk: '🚀 Пуски',
  launch: '🚀 Пуски',
  kab: '💣 КАБи',
  rszv: '💣 РСЗВ',
  rozved: '🔍 Розвідники',
  vibuh: '💥 Вибухи',
  explosion: '💥 Вибухи',
  alarm: '🚨 Тривога',
  alarm_cancel: '✅ Відбій',
  default: 'Загроза',
};
