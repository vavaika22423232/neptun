import { useEffect } from 'react';
import { AppState } from 'react-native';
import { dataStreamService } from '../../../services/dataStreamService';
import { mapDataService, parseAlarmData } from '../services/mapDataService';
import { applyBallisticFromApi } from './useBallisticMapOverlays';
import { useMapStore } from '../state/mapStore';

export function useLiveMapData(timeRange = 180): void {
  const setAlarmData = useMapStore((s) => s.setAlarmData);
  const setMarkerData = useMapStore((s) => s.setMarkerData);
  const upsertMarker = useMapStore((s) => s.upsertMarker);
  const patchTrack = useMapStore((s) => s.patchTrack);
  const deleteMarker = useMapStore((s) => s.deleteMarker);
  const setLinkPhase = useMapStore((s) => s.setLinkPhase);
  const touchSignificantRefresh = useMapStore((s) => s.touchSignificantRefresh);

  useEffect(() => {
    let cancelled = false;
    async function refresh() {
      setLinkPhase('connecting');
      const [alarms, markers] = await Promise.all([
        mapDataService.fetchAlarms(),
        mapDataService.fetchThreatMarkers(timeRange),
      ]);
      if (cancelled) return;
      setAlarmData(alarms);
      setMarkerData(markers);
      applyBallisticFromApi(markers.ballisticActive, markers.ballisticRegion);
      setLinkPhase('live');
      touchSignificantRefresh();
    }
    void refresh();
    const poll = setInterval(refresh, 30000);

    dataStreamService.connect();
    const offAlarm = dataStreamService.on('alarm_update', (payload) => {
      setAlarmData(parseAlarmData(payload));
      setLinkPhase('live');
      touchSignificantRefresh();
    });
    const offNew = dataStreamService.on('marker_new', (payload) => {
      if (payload._markersRefresh) void mapDataService.fetchThreatMarkers(timeRange).then(setMarkerData);
      else upsertMarker(payload);
      setLinkPhase('live');
      touchSignificantRefresh();
    });
    const offRefresh = dataStreamService.on('markers_refresh', () => {
      void mapDataService.fetchThreatMarkers(timeRange).then((data) => {
        setMarkerData(data);
        applyBallisticFromApi(data.ballisticActive, data.ballisticRegion);
      });
      setLinkPhase('live');
      touchSignificantRefresh();
    });
    const offUpdate = dataStreamService.on('marker_update', upsertMarker);
    const offTrack = dataStreamService.on('track_update', patchTrack);
    const offDelete = dataStreamService.on('marker_delete', (payload) => {
      const id = String(payload.id ?? '');
      if (id) deleteMarker(id);
    });
    const appStateSub = AppState.addEventListener('change', (state) => {
      if (state === 'active') dataStreamService.forceReconnect();
    });

    return () => {
      cancelled = true;
      clearInterval(poll);
      offAlarm();
      offNew();
      offRefresh();
      offUpdate();
      offTrack();
      offDelete();
      appStateSub.remove();
    };
  }, [deleteMarker, patchTrack, setAlarmData, setLinkPhase, setMarkerData, timeRange, upsertMarker]);
}
