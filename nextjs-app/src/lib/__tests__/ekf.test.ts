import assert from 'node:assert/strict';
import { KalmanFilter2D } from '../ekf';

function test(name: string, fn: () => void): void {
  try {
    fn();
    console.log(`ok - ${name}`);
  } catch (error) {
    console.error(`not ok - ${name}`);
    throw error;
  }
}

// ── Construction ─────────────────────────────────────────────────────────────

test('initializes state at the given position', () => {
  const kf = new KalmanFilter2D(48.5, 31.2, 0, 0);
  assert.ok(Math.abs(kf.state[0] - 48.5) < 1e-5);
  assert.ok(Math.abs(kf.state[1] - 31.2) < 1e-5);
});

test('converts initial speed and bearing — heading North: vx > 0, vy ≈ 0', () => {
  const kf = new KalmanFilter2D(50.0, 30.0, 180, 0);
  assert.ok(kf.state[2] > 0, `vx should be positive, got ${kf.state[2]}`);
  assert.ok(Math.abs(kf.state[3]) < 1e-8, `vy should be ~0, got ${kf.state[3]}`);
});

test('converts initial speed and bearing — heading East: vx ≈ 0, vy > 0', () => {
  const kf = new KalmanFilter2D(50.0, 30.0, 180, 90);
  assert.ok(Math.abs(kf.state[2]) < 1e-8, `vx should be ~0, got ${kf.state[2]}`);
  assert.ok(kf.state[3] > 0, `vy should be positive, got ${kf.state[3]}`);
});

// ── Predict ──────────────────────────────────────────────────────────────────

test('predict does nothing for dt = 0', () => {
  const kf = new KalmanFilter2D(48.0, 30.0, 100, 45);
  const latBefore = kf.state[0];
  kf.predict(0);
  assert.strictEqual(kf.state[0], latBefore);
});

test('predict advances position northward', () => {
  const kf = new KalmanFilter2D(50.0, 30.0, 180, 0);
  const latBefore = kf.state[0];
  kf.predict(3600);
  assert.ok(kf.state[0] > latBefore, `lat should increase after northward travel`);
});

test('predict grows position covariance over time', () => {
  const kf = new KalmanFilter2D(50.0, 30.0, 100, 90);
  const p00Before = kf.P[0][0];
  kf.predict(60);
  assert.ok(kf.P[0][0] > p00Before, 'P[0][0] should grow after predict');
});

// ── Update ───────────────────────────────────────────────────────────────────

test('update moves state toward measurement', () => {
  const kf = new KalmanFilter2D(50.0, 30.0, 0, 0, 1, 1);
  kf.update(50.5, 30.5, 0.9);
  assert.ok(kf.state[0] > 50.0, 'lat should move toward 50.5');
  assert.ok(kf.state[1] > 30.0, 'lng should move toward 30.5');
});

test('update reduces position covariance', () => {
  const kf = new KalmanFilter2D(50.0, 30.0, 0, 0, 10, 10);
  const p00Before = kf.P[0][0];
  for (let i = 0; i < 5; i++) {
    kf.predict(10);
    kf.update(50.0, 30.0, 1.0);
  }
  assert.ok(kf.P[0][0] < p00Before, 'covariance should shrink after updates');
});

test('high confidence measurement pulls state more than low confidence', () => {
  const kfHigh = new KalmanFilter2D(50.0, 30.0, 0, 0);
  const kfLow = new KalmanFilter2D(50.0, 30.0, 0, 0);
  kfHigh.update(51.0, 31.0, 0.99);
  kfLow.update(51.0, 31.0, 0.01);
  const deltaHigh = Math.abs(kfHigh.state[0] - 50.0);
  const deltaLow = Math.abs(kfLow.state[0] - 50.0);
  assert.ok(deltaHigh > deltaLow, `high confidence (${deltaHigh}) should pull more than low (${deltaLow})`);
});

test('update with singular S does not throw', () => {
  const kf = new KalmanFilter2D(50.0, 30.0, 0, 0, 0, 0, 0, 0);
  assert.doesNotThrow(() => kf.update(50.1, 30.1, 0.8));
});

// ── Convergence ──────────────────────────────────────────────────────────────

test('converges toward true position after 20 observations', () => {
  const trueLat = 49.8;
  const trueLng = 36.2;
  const kf = new KalmanFilter2D(50.0, 36.0, 150, 90);
  for (let i = 0; i < 20; i++) {
    kf.predict(30);
    kf.update(trueLat + (Math.random() - 0.5) * 0.01, trueLng + (Math.random() - 0.5) * 0.01, 0.8);
  }
  assert.ok(Math.abs(kf.state[0] - trueLat) < 0.1, `lat ${kf.state[0]} should be near ${trueLat}`);
  assert.ok(Math.abs(kf.state[1] - trueLng) < 0.1, `lng ${kf.state[1]} should be near ${trueLng}`);
});

// ── speedKmh() ───────────────────────────────────────────────────────────────

test('speedKmh() returns ~0 for stationary filter', () => {
  const kf = new KalmanFilter2D(50.0, 30.0, 0, 0);
  assert.ok(kf.speedKmh() < 1, `speed should be ~0, got ${kf.speedKmh()}`);
});

test('speedKmh() returns ~180 for 180 km/h North', () => {
  const kf = new KalmanFilter2D(50.0, 30.0, 180, 0);
  assert.ok(Math.abs(kf.speedKmh() - 180) < 2, `speed should be ~180, got ${kf.speedKmh()}`);
});

test('speedKmh() returns ~200 for 200 km/h East', () => {
  const kf = new KalmanFilter2D(50.0, 30.0, 200, 90);
  assert.ok(Math.abs(kf.speedKmh() - 200) < 2, `speed should be ~200, got ${kf.speedKmh()}`);
});

test('speedKmh() is ~same for all bearings at equal speed', () => {
  for (const bearing of [0, 45, 90, 135, 180, 225, 270, 315]) {
    const kf = new KalmanFilter2D(50.0, 30.0, 150, bearing);
    const s = kf.speedKmh();
    assert.ok(Math.abs(s - 150) < 2, `bearing ${bearing}: speed should be ~150, got ${s}`);
  }
});

// ── bearingDeg() ─────────────────────────────────────────────────────────────

test('bearingDeg() returns ~0 for North heading', () => {
  const kf = new KalmanFilter2D(50.0, 30.0, 150, 0);
  assert.ok(kf.bearingDeg() < 2 || kf.bearingDeg() > 358, `bearing should be ~0, got ${kf.bearingDeg()}`);
});

test('bearingDeg() returns ~90 for East heading', () => {
  const kf = new KalmanFilter2D(50.0, 30.0, 150, 90);
  assert.ok(Math.abs(kf.bearingDeg() - 90) < 2, `bearing should be ~90, got ${kf.bearingDeg()}`);
});

test('bearingDeg() returns ~180 for South heading', () => {
  const kf = new KalmanFilter2D(50.0, 30.0, 150, 180);
  assert.ok(Math.abs(kf.bearingDeg() - 180) < 2, `bearing should be ~180, got ${kf.bearingDeg()}`);
});

test('bearingDeg() returns ~270 for West heading', () => {
  const kf = new KalmanFilter2D(50.0, 30.0, 150, 270);
  assert.ok(Math.abs(kf.bearingDeg() - 270) < 2, `bearing should be ~270, got ${kf.bearingDeg()}`);
});

// ── positionSigmaKm() ────────────────────────────────────────────────────────

test('positionSigmaKm() returns positive value initially', () => {
  const kf = new KalmanFilter2D(50.0, 30.0, 0, 0, 0.5, 0.1);
  assert.ok(kf.positionSigmaKm() > 0, 'sigma should be positive');
});

test('positionSigmaKm() grows after predict and shrinks after updates', () => {
  const kf = new KalmanFilter2D(50.0, 30.0, 100, 45, 0.01, 0.001);
  const sigma0 = kf.positionSigmaKm();
  kf.predict(300);
  const sigmaAfterPredict = kf.positionSigmaKm();
  assert.ok(sigmaAfterPredict > sigma0, 'sigma should grow after predict');
  for (let i = 0; i < 5; i++) kf.update(50.0, 30.0, 0.9);
  assert.ok(kf.positionSigmaKm() < sigmaAfterPredict, 'sigma should shrink after updates');
});

// ── predictedPosition() ──────────────────────────────────────────────────────

test('predictedPosition() returns current position for dt = 0', () => {
  const kf = new KalmanFilter2D(50.0, 30.0, 100, 90);
  const pos = kf.predictedPosition(0);
  assert.ok(Math.abs(pos.lat - 50.0) < 1e-5, `lat should be 50.0, got ${pos.lat}`);
  assert.ok(Math.abs(pos.lng - 30.0) < 1e-5, `lng should be 30.0, got ${pos.lng}`);
});

test('predictedPosition() does NOT mutate filter state', () => {
  const kf = new KalmanFilter2D(50.0, 30.0, 150, 0);
  const stateBefore = [...kf.state];
  kf.predictedPosition(600);
  assert.deepEqual(kf.state, stateBefore, 'state should not be mutated');
});

test('predictedPosition() projects northward for North heading', () => {
  const kf = new KalmanFilter2D(50.0, 30.0, 180, 0);
  const pos = kf.predictedPosition(3600);
  assert.ok(pos.lat > 50.0, `lat should increase northward, got ${pos.lat}`);
});

// ── Serialization ─────────────────────────────────────────────────────────────

test('toJSON / fromJSON: state round-trips exactly', () => {
  const kf = new KalmanFilter2D(48.5, 31.2, 150, 220);
  kf.predict(60); kf.update(48.6, 31.3, 0.85);
  kf.predict(45); kf.update(48.7, 31.4, 0.9);

  const json = kf.toJSON();
  const restored = KalmanFilter2D.fromJSON(json);
  assert.ok(Math.abs(restored.state[0] - kf.state[0]) < 1e-10, 'lat state preserved');
  assert.ok(Math.abs(restored.state[1] - kf.state[1]) < 1e-10, 'lng state preserved');
  assert.ok(Math.abs(restored.state[2] - kf.state[2]) < 1e-10, 'vx state preserved');
  assert.ok(Math.abs(restored.state[3] - kf.state[3]) < 1e-10, 'vy state preserved');
});

test('toJSON / fromJSON: covariance matrix preserved', () => {
  const kf = new KalmanFilter2D(50.0, 30.0, 100, 45);
  kf.predict(120); kf.update(50.1, 30.1, 0.7);

  const restored = KalmanFilter2D.fromJSON(kf.toJSON());
  for (let i = 0; i < 4; i++) {
    for (let j = 0; j < 4; j++) {
      assert.ok(Math.abs(restored.P[i]![j]! - kf.P[i]![j]!) < 1e-10, `P[${i}][${j}] preserved`);
    }
  }
});

test('toJSON / fromJSON: noise params preserved', () => {
  const kf = new KalmanFilter2D(50.0, 30.0, 0, 0, 0.1, 1e-4, 2e-5, 5e-3);
  const restored = KalmanFilter2D.fromJSON(kf.toJSON());
  assert.strictEqual(restored.qProcessNoise, kf.qProcessNoise);
  assert.strictEqual(restored.rMeasurementNoise, kf.rMeasurementNoise);
});

test('toJSON / fromJSON: speedKmh and bearingDeg preserved', () => {
  const kf = new KalmanFilter2D(48.5, 31.2, 160, 220);
  kf.predict(60); kf.update(48.6, 31.1, 0.85);

  const restored = KalmanFilter2D.fromJSON(kf.toJSON());
  assert.ok(Math.abs(restored.speedKmh() - kf.speedKmh()) < 0.01, 'speedKmh preserved');
  assert.ok(Math.abs(restored.bearingDeg() - kf.bearingDeg()) < 0.01, 'bearingDeg preserved');
});

test('toJSON / fromJSON: JSON.stringify round-trip works', () => {
  const kf = new KalmanFilter2D(49.0, 32.0, 170, 220);
  const roundTripped = JSON.parse(JSON.stringify(kf.toJSON()));
  const restored = KalmanFilter2D.fromJSON(roundTripped);
  assert.ok(Math.abs(restored.state[0] - kf.state[0]) < 1e-8, 'JSON round-trip preserves lat');
});

test('restored filter continues predict/update without errors', () => {
  const kf = new KalmanFilter2D(50.0, 30.0, 150, 90);
  kf.predict(60); kf.update(50.0, 30.1, 0.8);

  const restored = KalmanFilter2D.fromJSON(kf.toJSON());
  assert.doesNotThrow(() => {
    restored.predict(30);
    restored.update(50.05, 30.15, 0.75);
  });
});
