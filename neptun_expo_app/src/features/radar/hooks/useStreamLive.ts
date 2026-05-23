import { useEffect, useState } from 'react';
import { dataStreamService } from '../../../services/dataStreamService';
import type { ConnectionStatus } from '../types/radar.types';

/** SSE connectivity hint for Radar status bar. */
export function useStreamLive(isStale: boolean): ConnectionStatus {
  const [live, setLive] = useState(false);
  const [connecting, setConnecting] = useState(true);

  useEffect(() => {
    dataStreamService.connect();
    const markLive = () => {
      setLive(true);
      setConnecting(false);
    };
    const offConnected = dataStreamService.on('connected', markLive);
    const offMarker = dataStreamService.on('marker_new', markLive);
    const offAlarm = dataStreamService.on('alarm_update', markLive);
    const t = setTimeout(() => setConnecting(false), 4000);
    return () => {
      clearTimeout(t);
      offConnected();
      offMarker();
      offAlarm();
    };
  }, []);

  if (isStale) return 'stale';
  if (live) return 'live';
  if (connecting) return 'connecting';
  return 'offline';
}
