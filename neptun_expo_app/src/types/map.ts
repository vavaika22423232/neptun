export type ThreatType =
  | 'shahed'
  | 'raketa'
  | 'avia'
  | 'artillery'
  | 'obstril'
  | 'fpv'
  | 'pusk'
  | 'kab'
  | 'rszv'
  | 'rozved'
  | 'vibuh'
  | 'alarm'
  | 'alarm_cancel'
  | string;

export type AlarmRow = {
  regionId?: string;
  regionName?: string;
  regionType?: 'State' | 'District' | string;
  activeAlerts?: Array<{ type?: string; [key: string]: unknown }>;
  [key: string]: unknown;
};

export type TrajectoryPoint = {
  lat: number;
  lng: number;
  etaMinutes: number;
  fraction: number;
};

export type AITrajectory = {
  startLat: number;
  startLng: number;
  endLat: number;
  endLng: number;
  sourceName: string;
  targetName: string;
  predicted: boolean;
};

export type ThreatTrackPoint = {
  lat: number;
  lng: number;
  ts: number;
};

export type ThreatMarker = {
  id?: string;
  trackId?: string;
  lat: number;
  lng: number;
  threatType: ThreatType;
  place: string;
  text: string;
  date: string;
  projectedPath?: TrajectoryPoint[];
  trajectory?: AITrajectory;
  etaMinutes?: number;
  distanceKm?: number;
  count?: number;
  confidence0_100?: number;
  placementMode?: string;
  confidence?: number;
  courseBearing?: number;
  tickerBearing?: number;
  courseDirection?: string;
  arrowDirection?: string;
  positions?: ThreatTrackPoint[];
  markerIcon?: string;
  updatedAt: number;
};

export type MapAlarmData = {
  stateAlarms: Record<string, boolean>;
  districtAlarms: Record<string, boolean>;
  stateThreatTypes: Record<string, ThreatType>;
  stateCount: number;
  districtCount: number;
  ballisticRegions: string[];
};

export type MapMarkerData = {
  markers: ThreatMarker[];
  counts: Record<string, number>;
  ballisticActive?: boolean | null;
  ballisticRegion?: string | null;
};
