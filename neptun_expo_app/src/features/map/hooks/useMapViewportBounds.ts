import { useCallback, useState } from 'react';
import { boundsFromMapboxVisible, type MapViewportBounds } from '../utils/viewportBounds';

type RegionFeature = {
  properties?: {
    visibleBounds?: number[][];
  };
};

export function useMapViewportBounds() {
  const [viewport, setViewport] = useState<MapViewportBounds | null>(null);

  const onRegionDidChange = useCallback((feature: RegionFeature) => {
    const next = boundsFromMapboxVisible(feature.properties?.visibleBounds);
    if (!next) return;
    setViewport((prev) => {
      if (
        prev &&
        Math.abs(prev.north - next.north) < 0.02 &&
        Math.abs(prev.south - next.south) < 0.02 &&
        Math.abs(prev.east - next.east) < 0.02 &&
        Math.abs(prev.west - next.west) < 0.02
      ) {
        return prev;
      }
      return next;
    });
  }, []);

  return { viewport, onRegionDidChange };
}
