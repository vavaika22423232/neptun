import { useEffect, useState } from 'react';

/** Flutter `native_map_page` pulse: 0.92→1.0 over 2000ms easeInOut. */
const PULSE_MIN = 0.92;
const PULSE_MAX = 1;
const PERIOD_MS = 2000;
const TICK_MS = 120;

/**
 * Drives MapLibre fill-opacity updates for alarm polygons (~8 Hz; Flutter repaints ~5 Hz).
 */
export function useAlarmPulse(active: boolean): number {
  const [pulse, setPulse] = useState(PULSE_MIN);

  useEffect(() => {
    if (!active) {
      setPulse(PULSE_MIN);
      return;
    }
    const started = performance.now();
    const id = setInterval(() => {
      const phase = ((performance.now() - started) % PERIOD_MS) / PERIOD_MS;
      const eased = 0.5 - 0.5 * Math.cos(phase * Math.PI * 2);
      setPulse(PULSE_MIN + eased * (PULSE_MAX - PULSE_MIN));
    }, TICK_MS);
    return () => clearInterval(id);
  }, [active]);

  return pulse;
}

/** Oblast alarm fill opacity (dark theme). */
export function oblastPulseFillOpacity(pulse: number): number {
  const t = (pulse - PULSE_MIN) / (PULSE_MAX - PULSE_MIN);
  return 0.32 + t * 0.16;
}

/** District alarm fill opacity. */
export function districtPulseFillOpacity(pulse: number): number {
  const t = (pulse - PULSE_MIN) / (PULSE_MAX - PULSE_MIN);
  return 0.55 + t * 0.17;
}
