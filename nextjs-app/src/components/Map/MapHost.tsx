import { memo } from 'react';
import type { Alarm, FusionTrajectory, Marker } from '@/types';
import MapLibreMap from '@/components/Map/MapLibreContainer';

export type MapHostProps = {
  markers: Marker[];
  alarms: Alarm[];
  fusionTrajectories: FusionTrajectory[];
  isAdmin?: boolean;
  onMarkerAction?: () => void;
  isEmbed?: boolean;
  ukraineOnly?: boolean;
};

function MapHostInner(props: MapHostProps) {
  return <MapLibreMap {...props} />;
}

function MapHost(props: MapHostProps) {
  return <MapHostInner {...props} />;
}

export default memo(MapHost);
