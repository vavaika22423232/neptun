/**
 * Linear 2D Kalman Filter for tracking targets in lat/lng space.
 * State vector: [lat, lng, vx, vy]
 *   vx  = latitude velocity (deg/sec, northward)
 *   vy  = longitude velocity (deg/sec, actual rate — raw lng change per second)
 *
 * Speed and bearing helpers (`speedKmh`, `bearingDeg`) correctly convert the
 * mixed-scale velocity components to metric values accounting for cos(lat).
 *
 * Numerical stability: P update uses Joseph form P = (I-KH)P(I-KH)ᵀ + KRKᵀ.
 * Anisotropic noise: measurement R is rotated along/across the current heading
 * to model geocode errors that are elongated along the flight corridor.
 */

export type KalmanFilterJSON = {
  state: [number, number, number, number];
  P: number[][];
  qProcessNoise: number;
  rMeasurementNoise: number;
  singularSkipCount?: number;
  /** Running variance of recent innovations for adaptive Q noise (P2-C). */
  innovationVarianceLat?: number;
  innovationVarianceLng?: number;
  innovationSamples?: number;
};

export class KalmanFilter2D {
  public state: [number, number, number, number];
  public P: number[][];
  public qProcessNoise: number;
  public rMeasurementNoise: number;
  /** How many consecutive update() calls were skipped due to singular S matrix. */
  public singularSkipCount: number = 0;
  /** Running exponentially-smoothed innovation variance for adaptive Q (P2-C). */
  public innovationVarianceLat: number = 0;
  public innovationVarianceLng: number = 0;
  public innovationSamples: number = 0;

  constructor(
    initialLat: number,
    initialLng: number,
    initialSpeedKmH: number = 0,
    initialBearingDeg: number = 0,
    initialPosCov: number = 0.1,
    initialVelCov: number = 1e-4,
    qProcessNoise: number = 1e-5,
    rMeasurementNoise: number = 1e-2,
  ) {
    this.qProcessNoise = qProcessNoise;
    this.rMeasurementNoise = rMeasurementNoise;

    const latRad = (initialLat * Math.PI) / 180;
    const cosLat = Math.cos(latRad);
    const speedDegPerSecNorth = (initialSpeedKmH / 3600) / 111.32;
    const bearingRad = (initialBearingDeg * Math.PI) / 180;

    const vx = speedDegPerSecNorth * Math.cos(bearingRad);
    const vyEast = speedDegPerSecNorth * Math.sin(bearingRad);
    const vy = cosLat > 1e-6 ? vyEast / cosLat : 0;

    this.state = [initialLat, initialLng, vx, vy];
    this.P = [
      [initialPosCov, 0, 0, 0],
      [0, initialPosCov, 0, 0],
      [0, 0, initialVelCov, 0],
      [0, 0, 0, initialVelCov],
    ];
  }

  get maneuverWeight(): number { return 0; }

  get lat(): number { return this.state[0]; }
  get lng(): number { return this.state[1]; }

  public resetPosition(lat: number, lng: number): void {
    this.state[0] = lat;
    this.state[1] = lng;
  }

  // ─── Predict step ──────────────────────────────────────────────────────────

  public predict(dtSeconds: number): void {
    if (dtSeconds <= 0) return;

    const [x, y, vx, vy] = this.state;

    this.state[0] = x + vx * dtSeconds;
    this.state[1] = y + vy * dtSeconds;

    const F = [
      [1, 0, dtSeconds, 0],
      [0, 1, 0, dtSeconds],
      [0, 0, 1, 0],
      [0, 0, 0, 1],
    ];

    const P_pred = this._matMul(this._matMul(F, this.P), this._transpose(F));

    const dt2 = (dtSeconds * dtSeconds) / 2;
    const dt3 = (dtSeconds * dtSeconds * dtSeconds) / 3;
    const q = this.qProcessNoise;
    const Q = [
      [q * dt3, 0, q * dt2, 0],
      [0, q * dt3, 0, q * dt2],
      [q * dt2, 0, q * dtSeconds, 0],
      [0, q * dt2, 0, q * dtSeconds],
    ];

    this.P = this._matAdd(P_pred, Q);
  }

  // ─── Update step ───────────────────────────────────────────────────────────

  /**
   * Standard isotropic update. Confidence in [0,1] scales R inversely.
   * Uses Joseph form for numerical stability of P.
   * Increments singularSkipCount on matrix singularity; resets on success.
   *
   * P2-B: Chi-square gate — reject outlier measurements whose Mahalanobis distance
   * exceeds χ²(2, p=0.997) ≈ 11.8 (3σ gate for 2 DoF). Prevents wild measurements
   * from corrupting the state estimate.
   *
   * P5-D: channelPriority in [1..5] lowers R (tighter trust) for high-priority channels.
   */
  public update(lat: number, lng: number, confidence: number = 0.8, channelPriority?: number, sensorType?: 'acoustic' | 'radar' | 'visual'): void {
    const H = [
      [1, 0, 0, 0],
      [0, 1, 0, 0],
    ];

    // P5-D: high-priority channels (p=1) get 40% lower measurement noise
    const priorityScale = (channelPriority != null && Number.isFinite(channelPriority))
      ? Math.max(0.6, 1 - (5 - Math.max(1, Math.min(5, channelPriority))) * 0.08)
      : 1;

    let r = (this.rMeasurementNoise / Math.max(0.01, confidence)) * priorityScale;
    if (sensorType === 'acoustic') r *= 25.0;
    else if (sensorType === 'radar') r *= 0.5;
    else if (sensorType === 'visual') r *= 2.0;

    const R = [
      [r, 0],
      [0, r],
    ];

    // P2-B: chi-square gate (3σ, 2 DoF, threshold ≈ 11.8).
    // Only applied when the filter has converged enough (≥3 innovations and position
    // uncertainty is small relative to the gate).  During warm-up, large innovations
    // are expected and should be accepted.
    const innovLat = lat - this.state[0];
    const innovLng = lng - this.state[1];
    const posUncertainty = this.P[0][0] + this.P[1][1]; // trace of position block
    const filterConverged = this.innovationSamples >= 3 && posUncertainty < 0.5;
    if (filterConverged) {
      const HP = this._matMul(H, this.P);
      const S = this._matAdd(this._matMul(HP, this._transpose(H)), R);
      const SI = this._invert2x2(S);
      if (SI) {
        const mahal2 = innovLat * (SI[0][0] * innovLat + SI[0][1] * innovLng)
                     + innovLng * (SI[1][0] * innovLat + SI[1][1] * innovLng);
        if (mahal2 > 11.8) {
          this.singularSkipCount += 1;
          return;
        }
      }
    }

    // P2-C: update running innovation variance for adaptive Q
    const alpha = this.innovationSamples < 20 ? 0.3 : 0.1;
    this.innovationVarianceLat = (1 - alpha) * this.innovationVarianceLat + alpha * innovLat * innovLat;
    this.innovationVarianceLng = (1 - alpha) * this.innovationVarianceLng + alpha * innovLng * innovLng;
    this.innovationSamples += 1;

    // P2-C: adapt process noise based on observed motion variability
    if (this.innovationSamples >= 5) {
      const observedNoise = Math.max(this.innovationVarianceLat, this.innovationVarianceLng);
      // Scale Q toward observed variability, clamped to [0.2×base, 5×base]
      const baseQ = this.qProcessNoise;
      const adaptedQ = Math.min(baseQ * 5, Math.max(baseQ * 0.2, observedNoise * 0.01));
      this.qProcessNoise = adaptedQ;
    }

    this._applyUpdate(H, R, lat, lng);
  }

  /**
   * Anisotropic update — reduces noise along the current flight heading and
   * inflates it perpendicular, modelling corridor-elongated geocode errors.
   * Falls back to isotropic when velocity is too small to give a reliable bearing.
   *
   * @param rAlong  noise scale along heading (< rMeasurementNoise = tighter)
   * @param rAcross noise scale across heading (> rMeasurementNoise = looser)
   */
  public updateAnisotropic(
    lat: number,
    lng: number,
    confidence: number = 0.8,
    rAlong = 0.4,
    rAcross = 2.5,
  ): void {
    const H = [
      [1, 0, 0, 0],
      [0, 1, 0, 0],
    ];

    const speedKmh = this.speedKmh();
    if (speedKmh < 20) {
      // Not enough velocity to know heading reliably — use isotropic
      this.update(lat, lng, confidence);
      return;
    }

    const baseR = this.rMeasurementNoise / Math.max(0.01, confidence);
    const bearingRad = (this.bearingDeg() * Math.PI) / 180;
    const cosB = Math.cos(bearingRad);
    const sinB = Math.sin(bearingRad);

    // Rotate diagonal [rAlong, rAcross] into lat/lng frame
    const rLat = rAlong * cosB * cosB + rAcross * sinB * sinB;
    const rLng = rAlong * sinB * sinB + rAcross * cosB * cosB;
    const rCross = (rAlong - rAcross) * cosB * sinB;

    const R = [
      [baseR * rLat, baseR * rCross],
      [baseR * rCross, baseR * rLng],
    ];

    this._applyUpdate(H, R, lat, lng);
  }

  private _applyUpdate(H: number[][], R: number[][], lat: number, lng: number): void {
    const y = [lat - this.state[0], lng - this.state[1]];

    const HP = this._matMul(H, this.P);
    const S = this._matAdd(this._matMul(HP, this._transpose(H)), R);

    const SI = this._invert2x2(S);
    if (!SI) {
      this.singularSkipCount += 1;
      return;
    }
    this.singularSkipCount = Math.max(0, this.singularSkipCount - 1);

    const PHt = this._matMul(this.P, this._transpose(H));
    const K = this._matMul(PHt, SI); // 4×2

    const Ky = [
      K[0][0] * y[0] + K[0][1] * y[1],
      K[1][0] * y[0] + K[1][1] * y[1],
      K[2][0] * y[0] + K[2][1] * y[1],
      K[3][0] * y[0] + K[3][1] * y[1],
    ];
    this.state[0] += Ky[0];
    this.state[1] += Ky[1];
    this.state[2] += Ky[2];
    this.state[3] += Ky[3];

    // Joseph form: P = (I-KH)P(I-KH)ᵀ + KRKᵀ — numerically stable, guaranteed PSD
    const I4 = [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]];
    const KH = this._matMul(K, H); // 4×4
    const IKH = this._matSub(I4, KH); // 4×4
    const KR = this._matMul(K, R); // 4×2
    const KRKt = this._matMul(KR, this._transpose(K)); // 4×4
    this.P = this._matAdd(
      this._matMul(this._matMul(IKH, this.P), this._transpose(IKH)),
      KRKt,
    );
  }

  // ─── Metric helpers ────────────────────────────────────────────────────────

  /**
   * Returns the current speed in km/h, correctly accounting for cos(lat)
   * when converting longitude velocity to metric East speed.
   */
  public speedKmh(): number {
    const lat = this.state[0];
    const vx = this.state[2];
    const vy = this.state[3];
    const cosLat = Math.cos((lat * Math.PI) / 180);
    const vNorthMs = vx * 111320;
    const vEastMs = vy * cosLat * 111320;
    const speedMs = Math.sqrt(vNorthMs ** 2 + vEastMs ** 2);
    return speedMs * 3.6;
  }

  /**
   * Returns the bearing in degrees (0 = North, 90 = East), correctly
   * accounting for cos(lat) on the East velocity component.
   */
  public bearingDeg(): number {
    const lat = this.state[0];
    const vx = this.state[2];
    const vy = this.state[3];
    const cosLat = Math.cos((lat * Math.PI) / 180);
    const vNorthMs = vx * 111320;
    const vEastMs = vy * cosLat * 111320;
    const rad = Math.atan2(vEastMs, vNorthMs);
    return (rad * 180 / Math.PI + 360) % 360;
  }

  /**
   * Returns the 1-σ position uncertainty in km (max of lat/lng standard deviations).
   */
  public positionSigmaKm(): number {
    const sigmaLatDeg = Math.sqrt(Math.max(0, this.P[0][0]));
    const sigmaLngDeg = Math.sqrt(Math.max(0, this.P[1][1]));
    const sigmaLatKm = sigmaLatDeg * 111.32;
    const cosLat = Math.cos((this.state[0] * Math.PI) / 180);
    const sigmaLngKm = sigmaLngDeg * cosLat * 111.32;
    return Math.max(sigmaLatKm, sigmaLngKm);
  }

  /**
   * Returns the predicted position at `dtSeconds` in the future WITHOUT
   * mutating the filter state (read-only projection).
   */
  public predictedPosition(dtSeconds: number): { lat: number; lng: number } {
    const [lat, lng, vx, vy] = this.state;
    return {
      lat: lat + vx * dtSeconds,
      lng: lng + vy * dtSeconds,
    };
  }

  /**
   * P2-E: Position-only update — applies gain only to the lat/lng state components
   * (K rows 2 and 3 are zeroed). Used for maritime_approach / estimated placements
   * where the reported coordinate is a calculated fraction, not a true observation,
   * so trusting it for velocity would corrupt the EKF velocity state.
   */
  public updatePositionOnly(lat: number, lng: number, confidence: number = 0.8): void {
    const H = [
      [1, 0, 0, 0],
      [0, 1, 0, 0],
    ];
    const r = this.rMeasurementNoise / Math.max(0.01, confidence);
    const R = [[r, 0], [0, r]];

    const y = [lat - this.state[0], lng - this.state[1]];
    const HP = this._matMul(H, this.P);
    const S = this._matAdd(this._matMul(HP, this._transpose(H)), R);
    const SI = this._invert2x2(S);
    if (!SI) { this.singularSkipCount += 1; return; }
    this.singularSkipCount = Math.max(0, this.singularSkipCount - 1);

    const PHt = this._matMul(this.P, this._transpose(H));
    const K = this._matMul(PHt, SI);
    // Zero-out velocity rows of K
    K[2] = [0, 0];
    K[3] = [0, 0];

    this.state[0] += K[0][0] * y[0] + K[0][1] * y[1];
    this.state[1] += K[1][0] * y[0] + K[1][1] * y[1];

    const I4 = [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]];
    const KH = this._matMul(K, H);
    const IKH = this._matSub(I4, KH);
    const KR = this._matMul(K, R);
    const KRKt = this._matMul(KR, this._transpose(K));
    this.P = this._matAdd(
      this._matMul(this._matMul(IKH, this.P), this._transpose(IKH)),
      KRKt,
    );
  }

  // ─── Serialization ─────────────────────────────────────────────────────────

  public toJSON(): KalmanFilterJSON {
    return {
      state: [...this.state] as [number, number, number, number],
      P: this.P.map((row) => [...row]),
      qProcessNoise: this.qProcessNoise,
      rMeasurementNoise: this.rMeasurementNoise,
      singularSkipCount: this.singularSkipCount,
      innovationVarianceLat: this.innovationVarianceLat,
      innovationVarianceLng: this.innovationVarianceLng,
      innovationSamples: this.innovationSamples,
    };
  }

  public static fromJSON(data: KalmanFilterJSON): KalmanFilter2D {
    const kf = new KalmanFilter2D(
      data.state[0],
      data.state[1],
      0, 0,
      1, 1,
      data.qProcessNoise,
      data.rMeasurementNoise,
    );
    kf.state = [...data.state] as [number, number, number, number];
    kf.P = data.P.map((row) => [...row]);
    kf.singularSkipCount = data.singularSkipCount ?? 0;
    kf.innovationVarianceLat = data.innovationVarianceLat ?? 0;
    kf.innovationVarianceLng = data.innovationVarianceLng ?? 0;
    kf.innovationSamples = data.innovationSamples ?? 0;
    return kf;
  }

  // ─── Matrix math ───────────────────────────────────────────────────────────

  private _matMul(a: number[][], b: number[][]): number[][] {
    const rows = a.length;
    const cols = b[0].length;
    const inner = b.length;
    const m: number[][] = Array.from({ length: rows }, () => new Array(cols).fill(0));
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        let s = 0;
        for (let i = 0; i < inner; i++) s += a[r][i] * b[i][c];
        m[r][c] = s;
      }
    }
    return m;
  }

  private _transpose(a: number[][]): number[][] {
    return a[0].map((_, c) => a.map((r) => r[c]));
  }

  private _matAdd(a: number[][], b: number[][]): number[][] {
    return a.map((r, i) => r.map((v, j) => v + b[i][j]));
  }

  private _matSub(a: number[][], b: number[][]): number[][] {
    return a.map((r, i) => r.map((v, j) => v - b[i][j]));
  }

  private _invert2x2(m: number[][]): number[][] | null {
    const det = m[0][0] * m[1][1] - m[0][1] * m[1][0];
    if (Math.abs(det) < 1e-12) return null;
    return [
      [m[1][1] / det, -m[0][1] / det],
      [-m[1][0] / det, m[0][0] / det],
    ];
  }
}

/**
 * P2-A: Interacting Multiple Model (IMM) filter for targets that can switch
 * motion modes (e.g. cruise → maneuver → loiter).  Two internal KalmanFilter2D
 * models run in parallel:
 *   model[0] — "constant velocity" (low Q — smooth cruise)
 *   model[1] — "constant acceleration" proxy (high Q — maneuvering)
 *
 * At each update step:
 *  1. Weights are mixed across models using the Markov transition matrix.
 *  2. Each model updates independently.
 *  3. Likelihood is computed and weights are renormalized.
 *  4. The fused state/covariance is the weighted sum of models.
 *
 * The active model weight (0–1 for model[1]) is exposed as `maneuverWeight` and
 * drives the P2-B jerk/maneuver flag in the tracker engine.
 */
export type IMMFilterJSON = {
  filters: [KalmanFilterJSON, KalmanFilterJSON];
  weights: [number, number];
  transitionProb: number;
};

export class IMMFilter2D {
  private filters: [KalmanFilter2D, KalmanFilter2D];
  private weights: [number, number];
  /** Off-diagonal transition probability (how likely is a mode switch per step) */
  private transitionProb: number;

  constructor(
    initLat: number,
    initLng: number,
    qLow: number = 1e-5,
    qHigh: number = 5e-4,
    rNoise: number = 1e-2,
    transitionProb: number = 0.05,
  ) {
    this.filters = [
      new KalmanFilter2D(initLat, initLng, 0, 0, 1, 1, qLow, rNoise),
      new KalmanFilter2D(initLat, initLng, 0, 0, 1, 1, qHigh, rNoise),
    ];
    this.weights = [0.7, 0.3];
    this.transitionProb = transitionProb;
  }

  get maneuverWeight(): number { return this.weights[1]; }

  get qProcessNoise(): number {
    return this.weights[0] * this.filters[0].qProcessNoise + this.weights[1] * this.filters[1].qProcessNoise;
  }

  get singularSkipCount(): number {
    return Math.max(this.filters[0].singularSkipCount, this.filters[1].singularSkipCount);
  }

  get lat(): number {
    return this.weights[0] * this.filters[0].state[0] + this.weights[1] * this.filters[1].state[0];
  }
  get lng(): number {
    return this.weights[0] * this.filters[0].state[1] + this.weights[1] * this.filters[1].state[1];
  }
  speedKmh(): number {
    return this.weights[0] * this.filters[0].speedKmh() + this.weights[1] * this.filters[1].speedKmh();
  }
  bearingDeg(): number {
    const b0 = this.filters[0].bearingDeg();
    const b1 = this.filters[1].bearingDeg();
    // Circular mean
    const r0x = Math.cos((b0 * Math.PI) / 180) * this.weights[0];
    const r0y = Math.sin((b0 * Math.PI) / 180) * this.weights[0];
    const r1x = Math.cos((b1 * Math.PI) / 180) * this.weights[1];
    const r1y = Math.sin((b1 * Math.PI) / 180) * this.weights[1];
    return ((Math.atan2(r0y + r1y, r0x + r1x) * 180) / Math.PI + 360) % 360;
  }
  positionSigmaKm(): number {
    return this.weights[0] * this.filters[0].positionSigmaKm() + this.weights[1] * this.filters[1].positionSigmaKm();
  }

  predictedPosition(dtSeconds: number): { lat: number; lng: number } {
    const p0 = this.filters[0].predictedPosition(dtSeconds);
    const p1 = this.filters[1].predictedPosition(dtSeconds);
    return {
      lat: this.weights[0] * p0.lat + this.weights[1] * p1.lat,
      lng: this.weights[0] * p0.lng + this.weights[1] * p1.lng,
    };
  }

  resetPosition(lat: number, lng: number): void {
    // Preserve velocities and noise, but reset coordinates
    this.filters[0].state[0] = lat;
    this.filters[0].state[1] = lng;
    this.filters[1].state[0] = lat;
    this.filters[1].state[1] = lng;
  }

  predict(dtSeconds: number): void {
    // IMM mixing step: mix states before individual prediction
    const tp = this.transitionProb;
    const w0 = this.weights[0] * (1 - tp) + this.weights[1] * tp;
    const w1 = this.weights[1] * (1 - tp) + this.weights[0] * tp;
    const sum = w0 + w1;
    this.weights = [w0 / sum, w1 / sum];

    for (const f of this.filters) f.predict(dtSeconds);
  }

  update(lat: number, lng: number, confidence: number, channelPriority?: number, sensorType?: 'acoustic' | 'radar' | 'visual'): void {
    const priorityScale = (channelPriority != null && Number.isFinite(channelPriority))
      ? Math.max(0.6, 1 - (5 - Math.max(1, Math.min(5, channelPriority))) * 0.08)
      : 1;

    const likelihoods: [number, number] = [1, 1];
    for (let i = 0; i < 2; i++) {
      const f = this.filters[i]!;
      const dlat = lat - f.state[0];
      const dlng = lng - f.state[1];
      
      let r = (f.rMeasurementNoise / Math.max(0.01, confidence)) * priorityScale;
      if (sensorType === 'acoustic') r *= 25.0;
      else if (sensorType === 'radar') r *= 0.5;
      else if (sensorType === 'visual') r *= 2.0;

      // 2D Gaussian likelihood from innovation
      const mahal2 = (dlat * dlat + dlng * dlng) / r;
      likelihoods[i] = Math.exp(-0.5 * Math.min(mahal2, 100));
      f.update(lat, lng, confidence, channelPriority, sensorType);
    }

    // Weight update
    const w0 = this.weights[0] * likelihoods[0];
    const w1 = this.weights[1] * likelihoods[1];
    const sum = w0 + w1;
    if (sum > 1e-12) {
      this.weights = [w0 / sum, w1 / sum];
    }
  }

  updatePositionOnly(lat: number, lng: number, confidence: number = 0.8): void {
    for (const f of this.filters) f.updatePositionOnly(lat, lng, confidence);
  }

  toJSON(): IMMFilterJSON {
    return {
      filters: [this.filters[0].toJSON(), this.filters[1].toJSON()],
      weights: [...this.weights] as [number, number],
      transitionProb: this.transitionProb,
    };
  }

  static fromJSON(data: IMMFilterJSON): IMMFilter2D {
    const imm = new IMMFilter2D(0, 0);
    imm.filters = [KalmanFilter2D.fromJSON(data.filters[0]), KalmanFilter2D.fromJSON(data.filters[1])];
    imm.weights = [...data.weights] as [number, number];
    imm.transitionProb = data.transitionProb;
    return imm;
  }
}

// ─── RTS Smoother ─────────────────────────────────────────────────────────────

function invertMatrix(M: number[][]): number[][] | null {
  const n = M.length;
  const A = M.map((row) => [...row]);
  const I = Array.from({ length: n }, (_, i) => Array.from({ length: n }, (_, j) => (i === j ? 1 : 0)));

  for (let i = 0; i < n; i++) {
    let pivot = i;
    for (let j = i + 1; j < n; j++) {
      if (Math.abs(A[j][i]) > Math.abs(A[pivot][i])) pivot = j;
    }
    if (Math.abs(A[pivot][i]) < 1e-12) return null; // Singular

    if (pivot !== i) {
      [A[i], A[pivot]] = [A[pivot], A[i]];
      [I[i], I[pivot]] = [I[pivot], I[i]];
    }

    const diag = A[i][i];
    for (let j = 0; j < n; j++) {
      A[i][j] /= diag;
      I[i][j] /= diag;
    }

    for (let j = 0; j < n; j++) {
      if (j !== i) {
        const factor = A[j][i];
        for (let k = 0; k < n; k++) {
          A[j][k] -= factor * A[i][k];
          I[j][k] -= factor * I[i][k];
        }
      }
    }
  }
  return I;
}

function matMul(A: number[][], B: number[][]): number[][] {
  const result = Array.from({ length: A.length }, () => Array(B[0].length).fill(0));
  for (let i = 0; i < A.length; i++) {
    for (let j = 0; j < B[0].length; j++) {
      for (let k = 0; k < B.length; k++) {
        result[i][j] += A[i][k] * B[k][j];
      }
    }
  }
  return result;
}

function transpose(A: number[][]): number[][] {
  return A[0].map((_, colIndex) => A.map((row) => row[colIndex]));
}

function matAdd(A: number[][], B: number[][]): number[][] {
  return A.map((row, i) => row.map((val, j) => val + B[i][j]));
}

function matSub(A: number[][], B: number[][]): number[][] {
  return A.map((row, i) => row.map((val, j) => val - B[i][j]));
}

/**
 * Retrospective Track Smoothing (RTS) pass over a sequence of observations.
 * Returns smoothed [lat, lng] points.
 */
export function rtsSmooth(
  observations: { lat: number; lng: number; ts: number; confidence: number }[],
  qProcessNoise: number = 1e-4,
  rMeasurementNoise: number = 1e-2,
): [number, number][] {
  if (observations.length < 2) return observations.map(o => [o.lat, o.lng]);

  const kf = new KalmanFilter2D(
    observations[0].lat,
    observations[0].lng,
    0, 0, 1, 1,
    qProcessNoise,
    rMeasurementNoise
  );

  const states: number[][] = [];
  const covariances: number[][][] = [];
  const predStates: number[][] = [];
  const predCovariances: number[][][] = [];
  const dts: number[] = [];

  // Forward pass
  for (let i = 0; i < observations.length; i++) {
    const obs = observations[i];
    if (i > 0) {
      const dt = (obs.ts - observations[i - 1].ts) / 1000;
      dts.push(dt);
      if (dt > 0) kf.predict(dt);
    } else {
      dts.push(0);
    }

    predStates.push([...kf.state]);
    predCovariances.push(kf.P.map(row => [...row]));

    kf.update(obs.lat, obs.lng, obs.confidence);

    states.push([...kf.state]);
    covariances.push(kf.P.map(row => [...row]));
  }

  const smoothedStates = [...states];
  const smoothedCovs = [...covariances];

  // Backward RTS pass
  for (let i = observations.length - 2; i >= 0; i--) {
    const dt = dts[i + 1];
    const F = [
      [1, 0, dt, 0],
      [0, 1, 0, dt],
      [0, 0, 1, 0],
      [0, 0, 0, 1],
    ];

    const P_pred_inv = invertMatrix(predCovariances[i + 1]);
    if (!P_pred_inv) continue;

    // C = P * F^T * P_pred^-1
    const C = matMul(matMul(covariances[i], transpose(F)), P_pred_inv);

    // x_smooth = x + C * (x_smooth_next - x_pred)
    const x_diff = [
      [smoothedStates[i + 1][0] - predStates[i + 1][0]],
      [smoothedStates[i + 1][1] - predStates[i + 1][1]],
      [smoothedStates[i + 1][2] - predStates[i + 1][2]],
      [smoothedStates[i + 1][3] - predStates[i + 1][3]],
    ];
    const correction = matMul(C, x_diff);
    smoothedStates[i][0] += correction[0][0];
    smoothedStates[i][1] += correction[1][0];
    smoothedStates[i][2] += correction[2][0];
    smoothedStates[i][3] += correction[3][0];

    // P_smooth = P + C * (P_smooth_next - P_pred) * C^T
    const P_diff = matSub(smoothedCovs[i + 1], predCovariances[i + 1]);
    smoothedCovs[i] = matAdd(covariances[i], matMul(matMul(C, P_diff), transpose(C)));
  }

  return smoothedStates.map(s => [s[0], s[1]]);
}
