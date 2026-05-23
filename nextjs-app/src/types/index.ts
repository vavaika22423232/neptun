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

export interface TargetAssociationDebug {
  score: number;
  threshold: number;
  distance_km: number;
  radius_km: number;
  same_place: boolean;
  same_upstream_track: boolean;
  count_penalty: number;
  bearing_penalty: number;
  corridor_penalty: number;
  innovation_penalty: number;
  quality_penalty?: number;
  group_bonus?: number;
  text_intent?: string;
  observation_quality?: string;
  accepted: boolean;
  reason: string;
}

export interface MarkerTrackerTruth {
  reported_position?: TrackPosition;
  fused_position?: TrackPosition;
  predicted_position?: TrackPosition;
  coordinate_role?: 'observation' | 'target' | 'area_centroid' | 'estimated_path';
  public_position_policy?: 'precise_pin' | 'hold_existing' | 'zone_only' | 'suppress_or_admin_only';
  observation_quality?: 'observed' | 'estimated' | 'coarse' | 'target_hint';
  text_intent?: 'single' | 'group' | 'additional' | 'loss' | 'unknown';
  confidence_radius_km?: number;
  reasons?: string[];
}

export interface Marker {
  id?: string;
  track_id?: string;            // Track identifier: "trk_{type}_{group_id}" — groups updates for same threat
  lat: number;
  lng: number;
  rendered_lat?: number;
  rendered_lng?: number;
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
  last_observation?: TrackPosition;
  predicted_position?: TrackPosition;
  last_measurement?: TrackPosition;
  last_association?: TargetAssociationDebug;
  /** Quality of the latest accepted tracker observation: direct point, estimated, coarse, or target-only hint. */
  last_observation_quality?: 'observed' | 'estimated' | 'coarse' | 'target_hint';
  /** Text-level intent inferred by tracker: single target, group, additional target, loss report, or unknown. */
  last_text_intent?: 'single' | 'group' | 'additional' | 'loss' | 'unknown';
  /** Honest radar semantics for debug/admin/public UI: raw report vs fused/predicted position and display policy. */
  tracker_truth?: MarkerTrackerTruth;
  association_score?: number;
  association_reason?: string;
  /** Renderer-computed trail [[lat,lng],…] oldest→newest (P3-A) */
  tracker_trail?: [number, number][];
  /** Renderer-computed target destination [lat,lng] (P3-A) */
  tracker_target?: [number, number] | null;
  /** How the lat/lng was derived: 'ekf' | 'raw' */
  position_source?: string;
  /** Radar truthfulness state: observed=fresh evidence, coasting=physics projection, estimated=target-only, stale/lost=no fresh track. */
  radar_state?: 'observed' | 'estimated' | 'coasting' | 'stale' | 'lost' | 'manual';
  /** 1-sigma-ish uncertainty radius for current rendered position. */
  uncertainty_radius_km?: number;
  /** Evidence tier used by public/admin UI. */
  evidence_level?: 'manual' | 'priority_source' | 'multi_source' | 'single_source';
  /** Last real observation timestamp, not advanced by render extrapolation. */
  last_real_observation_at?: number;
  /** Timestamp when server computed the rendered radar position. */
  last_render_update_at?: number;
  /** Composite track quality index 0–100 (obs density + EKF health + source diversity). */
  tqi?: number;
  /** Resolved GADM HASC_1 oblast code for the current tracker position. */
  tracker_oblast_hasc?: string;
  /** Impact uncertainty ellipse: 1-σ radius around predicted end point. */
  impact_zone_km?: number;
  /** Formation group id when this track is part of a detected tactical formation. */
  formation_id?: string;
  /** Altitude mode inferred from message text. */
  altitude_mode?: 'low_altitude' | 'ballistic_arc' | 'unknown';
  /** Whether this track is transitioning from sea to land. */
  coastal_transition?: boolean;
  /** Worker-supplied confidence in the trajectory (0..1). */
  trajectory_confidence?: number;
  // ── tracker-plan-v4 fields ───────────────────────────────────────────────
  /** Burst score 0..1: how dense recent observations are vs. track average (P1-C). */
  burst_score?: number;
  /** True when jerk signal indicates active maneuver (P2-B). */
  maneuver_detected?: boolean;
  /** P10 ETA — slower bound of probabilistic ETA estimate, seconds (P2-C). */
  eta_p10?: number | null;
  /** P90 ETA — faster bound of probabilistic ETA estimate, seconds (P2-C). */
  eta_p90?: number | null;
  /** Swarm flock centroid when this target belongs to a computed cluster (P3-A). */
  swarm_centroid?: { lat: number; lng: number; size: number };
  /** Cross-oblast wave correlation score 0..1 (P3-B). */
  cross_oblast_score?: number;
  /** Split angle was shallow (< 45°) — lane separation not a hard turn (P3-C). */
  split_shallow_angle?: boolean;
  /** Ghost pool handoff origin track id (P3-E). */
  ghost_pool_origin?: string;
  /** Negative evidence score 0..1 — higher = more all-clear / intercept signals (P5-B). */
  negative_evidence_score?: number;
  /** Inferred launch origin from backward projection (P5-C). */
  origin_inference?: { lat: number; lng: number; confidence: number; method: string };
  /** Trajectory accuracy feedback from confirmed impact (P5-D). */
  trajectory_feedback?: { error_km: number; reported_at: number };
  /** Previous threat type if reclassified dynamically (P5-E). */
  threat_type_reclassified_from?: string;
}

export interface Trajectory {
  start?: [number, number];
  end?: [number, number];
  predicted?: boolean;
  source?: 'direction' | 'cardinal' | 'correlation' | 'ai' | 'ai_analyzer' | 'heuristic' | 'ekf_projection' | 'target_city' | 'group_bearing';
  prediction_confidence?: number;
  waypoints?: [number, number][];   // intermediate points for sea/complex routes
  flight_phase?: 'launch' | 'cruise' | 'approach' | 'circling';
  origin_coords?: [number, number]; // original point where threat was first detected (e.g. Sumy)
  /** Worker-supplied trajectory confidence propagated to map display opacity. */
  trajectory_confidence?: number;
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
