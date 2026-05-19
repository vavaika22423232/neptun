export type TrackMotionProfile = {
  nominalSpeedKmh: number;
  maxSpeedKmh: number;
  observedFreshMs: number;
  extrapolateMs: number;
  staleMs: number;
  lostMs: number;
  confidenceHalfLifeMs: number;
  targetStopKm: number;
  /** EKF process noise Q (higher = more maneuverable, filter trusts measurements more) */
  ekfProcessNoise: number;
  /** EKF measurement noise R base (higher = noisier observations) */
  ekfMeasurementNoise: number;
  /** Nominal altitude in meters for 2.5D kinematics and terrain masking */
  nominalAltitudeMeters: number;
};

const UAV_PROFILE: TrackMotionProfile = {
  nominalSpeedKmh: 170,
  maxSpeedKmh: 350,
  observedFreshMs: 90_000,
  extrapolateMs: 14 * 60_000,
  staleMs: 24 * 60_000,
  lostMs: 40 * 60_000,
  confidenceHalfLifeMs: 16 * 60_000,
  targetStopKm: 5,
  ekfProcessNoise: 1e-5,    // UAV: relatively predictable cruise
  ekfMeasurementNoise: 1e-2, // Moderate geocode noise
  nominalAltitudeMeters: 200, // Low-flying
};

const MISSILE_PROFILE: TrackMotionProfile = {
  nominalSpeedKmh: 850,
  maxSpeedKmh: 1200,
  observedFreshMs: 35_000,
  extrapolateMs: 4 * 60_000,
  staleMs: 7 * 60_000,
  lostMs: 10 * 60_000,
  confidenceHalfLifeMs: 4 * 60_000,
  targetStopKm: 12,
  ekfProcessNoise: 5e-5,    // Cruise missiles can maneuver significantly
  ekfMeasurementNoise: 5e-3, // Higher-precision radar observations
  nominalAltitudeMeters: 50,  // Cruise missiles fly very low
};

export const TRACK_MOTION_PROFILES: Record<string, TrackMotionProfile> = {
  shahed: UAV_PROFILE,
  drone: UAV_PROFILE,
  uav: UAV_PROFILE,
  fpv: {
    ...UAV_PROFILE,
    nominalSpeedKmh: 120,
    maxSpeedKmh: 250,
    extrapolateMs: 8 * 60_000,
    staleMs: 14 * 60_000,
    lostMs: 20 * 60_000,
    targetStopKm: 3,
    ekfProcessNoise: 2e-4,    // FPV: highly maneuverable, erratic flight
    ekfMeasurementNoise: 1.5e-2,
    nominalAltitudeMeters: 50,
  },
  rozved: {
    ...UAV_PROFILE,
    nominalSpeedKmh: 110,
    maxSpeedKmh: 300,
    extrapolateMs: 15 * 60_000,
    ekfProcessNoise: 8e-6,    // Recon drones: predictable loiter patterns
    ekfMeasurementNoise: 1e-2,
    nominalAltitudeMeters: 3000,
  },
  air_balloon: {
    nominalSpeedKmh: 40,
    maxSpeedKmh: 140,
    observedFreshMs: 5 * 60_000,
    extrapolateMs: 60 * 60_000,
    staleMs: 2 * 60 * 60_000,
    lostMs: 4 * 60 * 60_000,
    confidenceHalfLifeMs: 55 * 60_000,
    targetStopKm: 8,
    ekfProcessNoise: 1e-6,    // Balloons: wind-driven, very smooth trajectory
    ekfMeasurementNoise: 2e-2,
    nominalAltitudeMeters: 5000,
  },
  missile: MISSILE_PROFILE,
  raketa: MISSILE_PROFILE,
  krylata: MISSILE_PROFILE,
  pusk: MISSILE_PROFILE,
  ballistic: {
    nominalSpeedKmh: 2400,
    maxSpeedKmh: 5000,
    observedFreshMs: 20_000,
    extrapolateMs: 90_000,
    staleMs: 3 * 60_000,
    lostMs: 5 * 60_000,
    confidenceHalfLifeMs: 75_000,
    targetStopKm: 20,
    ekfProcessNoise: 1e-6,    // Ballistic: near-deterministic parabolic arc
    ekfMeasurementNoise: 1e-3,
    nominalAltitudeMeters: 40000,
  },
  kab: {
    nominalSpeedKmh: 600,
    maxSpeedKmh: 1000,
    observedFreshMs: 60_000,
    extrapolateMs: 6 * 60_000,
    staleMs: 10 * 60_000,
    lostMs: 16 * 60_000,
    confidenceHalfLifeMs: 7 * 60_000,
    targetStopKm: 8,
    ekfProcessNoise: 3e-5,
    ekfMeasurementNoise: 5e-3,
    nominalAltitudeMeters: 5000,
  },
  rszv: {
    nominalSpeedKmh: 650,
    maxSpeedKmh: 900,
    observedFreshMs: 45_000,
    extrapolateMs: 5 * 60_000,
    staleMs: 8 * 60_000,
    lostMs: 12 * 60_000,
    confidenceHalfLifeMs: 5 * 60_000,
    targetStopKm: 6,
    ekfProcessNoise: 4e-5,
    ekfMeasurementNoise: 5e-3,
    nominalAltitudeMeters: 2000,
  },
  avia: {
    nominalSpeedKmh: 750,
    maxSpeedKmh: 900,
    observedFreshMs: 2 * 60_000,
    extrapolateMs: 15 * 60_000,
    staleMs: 25 * 60_000,
    lostMs: 45 * 60_000,
    confidenceHalfLifeMs: 18 * 60_000,
    targetStopKm: 10,
    ekfProcessNoise: 6e-5,    // Aircraft: can maneuver freely
    ekfMeasurementNoise: 8e-3,
    nominalAltitudeMeters: 8000,
  },
};

export const DEFAULT_TRACK_MOTION_PROFILE: TrackMotionProfile = {
  nominalSpeedKmh: 180,
  maxSpeedKmh: 350,
  observedFreshMs: 90_000,
  extrapolateMs: 10 * 60_000,
  staleMs: 18 * 60_000,
  lostMs: 30 * 60_000,
  confidenceHalfLifeMs: 12 * 60_000,
  targetStopKm: 5,
  ekfProcessNoise: 1e-5,
  ekfMeasurementNoise: 1e-2,
  nominalAltitudeMeters: 500,
};

export function trackMotionProfile(threatType: string): TrackMotionProfile {
  return TRACK_MOTION_PROFILES[threatType] ?? DEFAULT_TRACK_MOTION_PROFILE;
}

/**
 * P7-F: Wind Vector Modeling
 * Returns the wind vector [vx, vy] in m/s (North, East) at the given location and altitude.
 * Prototype uses a hardcoded simulated wind field (e.g. 10 m/s from the North-West).
 */
export function getWindVector(lat: number, lng: number, altitudeMeters: number): { vx: number; vy: number } {
  // Prototype: 10 m/s wind from NW (so it blows towards SE)
  // vx (North) = -7.07 m/s
  // vy (East) = 7.07 m/s
  // Scale wind by altitude (stronger higher up)
  const scale = Math.min(1.5, Math.max(0.5, Math.log10(Math.max(10, altitudeMeters)) / 3));
  return { vx: -7.07 * scale, vy: 7.07 * scale };
}
