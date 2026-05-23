import { useEffect, useState } from 'react';
import { markerMotionEngine, type MotionCoord } from '../engine/markerMotionEngine';

/** Live interpolated positions for native MapLibre (60fps rAF). */
export function useMarkerMotionOverlay(): Map<string, MotionCoord> {
  const [positions, setPositions] = useState<Map<string, MotionCoord>>(() => new Map());

  useEffect(() => {
    return markerMotionEngine.subscribe((frame) => {
      setPositions((prev) => {
        const next = new Map(prev);
        for (const [key, coord] of frame) next.set(key, coord);
        return next;
      });
    });
  }, []);

  return positions;
}
