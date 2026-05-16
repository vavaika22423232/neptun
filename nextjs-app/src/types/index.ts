// ============================================
// Core domain types for NEPTUN
// ============================================

/** Public map position semantics (computed in build-markers, not raw worker placement_mode). */
export type MarkerDisplayClass =
  | 'region_signal'
  | 'corridor_or_bearing'
  | 'corroborated_point'
  | 'manual_override';

export interface TrackPosition {
  lat: number;
  lng: number;
  ts: number;       // Unix ms timestamp
  source?: string;  // channel name or 'chain_update'
  bearing?: number; // computed bearing at this point
}

export interface RejectedTrackObservation extends TrackPosition {
  reason?: string;
  confidence?: number;
}

export interface Marker {
  id?: string;
  track_id?: string;            // Track identifier: "trk_{type}_{group_id}" — groups updates for same threat
  lat: number;
  lng: number;
  threat_type: string;
  /** Legacy/raw threat type alias emitted by older producers. Prefer `threat_type`. */
  type?: string;
  place?: string;
  region?: string;
  /** Oblast label from ingest (often overlaps with `region`). */
  oblast?: string;
  text?: string;
  date?: string;
  count?: number;
  /** Filename under `/public` (e.g. `fpvdrone.png` from ingest); overrides `THREAT_ICONS[threat_type]` in MapContainer. */
  marker_icon?: string;
  course_bearing?: number | null;
  course_direction?: string;
  arrow_direction?: string;
  distance_km?: number;
  speed_kmh?: number;
  computed_speed_kmh?: number;   // Speed computed from real track positions (not estimated)
  prediction_confidence?: number;
  confidence_level?: string;
  trajectory_source?: 'direction' | 'cardinal' | 'correlation' | 'ai' | 'ai_analyzer' | 'heuristic' | string;
  trajectory?: Trajectory | null;
  created_at_epoch?: number;     // Unix ms — server timestamp when marker was created
  last_update_epoch?: number;    // Unix ms — last time this marker was updated (observation or ticker)
  origin?: string;               // Launch origin (e.g. "Крим", "Чорне море")
  flight_phase?: 'launch' | 'cruise' | 'approach' | 'circling';
  ticker_bearing?: number | null; // Bearing computed from trajectory (for server ticker movement)
  positions?: TrackPosition[];   // Full trail: observations + ticker projections (for display)
  observations?: TrackPosition[]; // Pristine channel observations only (for speed computation)
  rejected_observations?: RejectedTrackObservation[]; // Held/rejected evidence; never used for speed.
  observation_count?: number;    // Number of messages/observations for this track
  is_estimated?: boolean;
  /** Server track estimator state for motion realism and UI trust. */
  track_state?: 'observed' | 'extrapolated' | 'stale' | 'lost' | 'static' | 'manual' | 'split_candidate';
  /** 0..1 visual confidence after age/type-specific decay. */
  track_confidence?: number;
  /** Reason code from the server motion estimator. */
  motion_reason?: string;
  /** Last real observation timestamp in Unix ms; ticker updates must not move it forward. */
  last_observation_epoch?: number;
  /** 0–100 mirror of worker `confidence` for UI thresholds */
  confidence_0_100?: number;
  /** Worker map policy: point | approximate | predictive | suppressed_* */
  placement_mode?: string;
  confidence?: number;
  /**
   * Pipeline resolution status. Server may set `region_mismatch` when stated `region`/`oblast` /
   * `resolved_oblast_hasc` disagrees with geocode — coords were snapped to oblast centroid.
   */
  resolve_status?: string;
  /**
   * Stable key for the administrative area the worker intended (e.g. `kv`, `kharkiv_obl`), used by
   * the spatial correlator to avoid merging markers across different regions.
   */
  region_key?: string;
  /**
   * GADM HASC_1 code (e.g. `UA.KK`) from the worker’s NLP — preferred for region↔coord checks.
   */
  resolved_oblast_hasc?: string;
  /** Numeric oblast id if the worker uses internal ids — correlator gate when present. */
  oblast_id?: string | number;
  /** Alternative geocode candidates for debugging / future re-ranking (worker). */
  candidates?: unknown;
  /** Worker / ingest: multi | point | … — informs display policy when corroboration missing. */
  geocode_tier?: string;
  geo_decision_reason?: string;
  geocode_source?: string;
  /** Optional explicit candidate count when `candidates` is not an array on the wire. */
  candidates_count?: number;
  /** Ingest manual flag — operator-placed. */
  manual?: boolean;
  /** Server-computed: how much to trust a single point on the public map. */
  display_class?: MarkerDisplayClass;
  /** If false, client draws uncertainty circle (still uses threat-type icon). */
  show_precise_pin?: boolean;
  /** Radius in km for Leaflet circle (meters = km * 1000). */
  display_uncertainty_km?: number;
  /** First line for popup/tooltip (Ukrainian). */
  display_trust_hint_uk?: string;
  /** Deterministic server publication class. */
  publication_class?: 'VERIFIED_PUBLIC' | 'ADMIN_ONLY' | 'QUARANTINED' | 'REJECTED';
  /** Final min-dimensional publication confidence, 0..1. */
  publication_score?: number;
  /** Deterministic reason codes from publication policy. */
  publication_reasons?: string[];
  /** Stable raw/evidence fingerprint used for replay and audit. */
  event_fingerprint?: string;
  /** Stateful target lifecycle, separate from raw ingest row. */
  target_lifecycle_state?: 'DETECTED' | 'TRACKING' | 'CONFIRMED' | 'LOST' | 'STALE' | 'DESTROYED' | 'REJECTED';
  target_confidence?: number;
  source_count?: number;
  /** Client behavior profile for animation / life state. */
  behavior_kind?: string;
  behavior_pulse_ms?: number;
  /** Розбиття на карті (client-only): одиниця у «рої» з поля `count`. */
  swarm_unit_index?: number;
  /** Скільки пінів намалювано (до SWARM_VISUAL_MAX). */
  swarm_total?: number;

  // ── Drone tracker renderer fields ───────────────────────────────────────────
  /** Drone is loitering / orbiting — use circular animation, no directional arrow. */
  is_loitering?: boolean;
  /**
   * How heading was derived:
   * 'explicit' = text said 'курсом на X' | 'track' = sequential events |
   * 'regional' = entry corridor heuristic | 'unknown' = no data
   */
  heading_confidence?: 'explicit' | 'track' | 'regional' | 'unknown';
  /** Position was back-projected from target coords, not directly observed. */
  position_estimated?: boolean;
  /** Seconds until drone reaches target. null if not computable. */
  eta_seconds?: number | null;
  /**
   * 0–100 display confidence:
   * ≥90 solid pin + solid arrow | 70–89 semi arrow | 50–69 dashed | <50 area circle
   */
  display_confidence?: number;
  /** Age in ms since the last real telemetry observation. */
  age_ms?: number;
}

export interface Trajectory {
  start?: [number, number];
  end?: [number, number];
  predicted?: boolean;
  source?: 'direction' | 'cardinal' | 'correlation' | 'ai' | 'ai_analyzer' | 'heuristic';
  prediction_confidence?: number;
  waypoints?: [number, number][];   // intermediate points for sea/complex routes
  flight_phase?: 'launch' | 'cruise' | 'approach' | 'circling';
  origin_coords?: [number, number]; // original point where threat was first detected (e.g. Sumy)
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
  target?: string;
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
  isPro?: boolean;
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

// Threat type icon mapping (must match original index.html exactly).
// Custom per-marker icons use `marker_icon` on the marker (not listed here), e.g. `fpvdrone.png` for @kherson_non_drone.
export const THREAT_ICONS: Record<string, string> = {
  shahed: 'shahed3.webp',
  air_balloon: 'icon_air_balloon.svg',
  drone: 'shahed3.webp',
  uav: 'shahed3.webp',          // parser alias
  raketa: 'icon_balistic.svg',
  missile: 'icon_balistic.svg', // parser alias
  avia: 'icon_avia.svg',
  /** Ту-95 / стратегічна авіація (ingest: `threat_type: "tu95"` або `marker_icon: "icon_tu95.svg"`) */
  tu95: 'icon_tu95.svg',
  tu_95: 'icon_tu95.svg',
  strategic_bomber: 'icon_tu95.svg',
  artillery: 'artillery.png',
  obstril: 'icon_obstril.svg',
  fpv: 'fpv.png',
  pusk: 'icon_balistic.svg',
  launch: 'icon_balistic.svg',   // parser alias
  ballistic: 'icon_balistic.svg', // distinct ballistic missile icon
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
  air_balloon: '🎈 Повітряна куля',
  drone: '🛩️ Шахеди/БПЛА',
  uav: '🛩️ Шахеди/БПЛА',
  raketa: '🚀 Ракети',
  missile: '🚀 Ракети',
  avia: '✈️ Авіація',
  tu95: '✈️ Ту-95 (стратегічна авіація)',
  tu_95: '✈️ Ту-95 (стратегічна авіація)',
  strategic_bomber: '✈️ Стратегічна авіація',
  artillery: '💥 Артилерія',
  obstril: '💥 Обстріл',
  fpv: '🎯 FPV дрони',
  pusk: '🚀 Пуски',
  launch: '🚀 Пуски',
  ballistic: '☄️ Балістика',
  kab: '💣 КАБи',
  rszv: '💣 РСЗВ',
  rozved: '🔍 Розвідники',
  vibuh: '💥 Вибухи',
  explosion: '💥 Вибухи',
  alarm: '🚨 Тривога',
  alarm_cancel: '✅ Відбій',
  default: 'Загроза',
};
