import Mapbox from '@rnmapbox/maps';
import type { ElementRef } from 'react';
import { useEffect, useMemo, useRef, useState } from 'react';
import {
  districtPulseFillOpacity,
  oblastPulseFillOpacity,
  useAlarmPulse,
} from '../hooks/useAlarmPulse';
import { useMapViewportBounds } from '../hooks/useMapViewportBounds';
import { useMarkerMotionOverlay } from '../hooks/useMarkerMotionOverlay';
import { cullMarkersForDisplay } from '../utils/cullMarkersForDisplay';
import { mergeMotionIntoMarkers } from '../utils/mergeMotionMarkers';
import { Platform, StyleSheet, View } from 'react-native';
import { AppConstants } from '../../../config/constants';
import { ProFeature, ProGate } from '../../../core/pro/proGate';
import { useApp } from '../../../context/AppContext';
import { useAppTheme, useLegacyColors, useThemedStyles } from '../../../theme/useAppTheme';
import { useMapStore } from '../state/mapStore';
import {
  EMPTY_FEATURE_COLLECTION,
  markersToFeatureCollection,
  trajectoriesToFeatureCollection,
} from '../utils/geojson';
import {
  buildDistrictAlarmGeoJson,
  buildDistrictBorderGeoJson,
  DISTRICT_ALARM_FILL,
} from '../utils/districtGeoLoader';
import { buildOblastAlarmGeoJson } from '../utils/oblastGeoLoader';
import { tacticalDarkMapStyle, tacticalLightMapStyle } from '../utils/mapStyle';

if (typeof Mapbox.setTelemetryEnabled === 'function') {
  Mapbox.setTelemetryEnabled(false);
}
if (typeof Mapbox.setAccessToken === 'function') {
  Mapbox.setAccessToken(process.env.EXPO_PUBLIC_MAPBOX_ACCESS_TOKEN || 'pk.neptun-preview-token');
}

export function TacticalMap() {
  const c = useLegacyColors();
  const styles = useMapStyles();
  const { theme } = useAppTheme();
  const mapStyleJson = useMemo(
    () => JSON.stringify(theme.scheme === 'light' ? tacticalLightMapStyle : tacticalDarkMapStyle),
    [theme.scheme],
  );
  const cameraRef = useRef<ElementRef<typeof Mapbox.Camera>>(null);
  const { isPremium } = useApp();
  const markers = useMapStore((s) => s.markers);
  const visibleThreatTypes = useMapStore((s) => s.visibleThreatTypes);
  const alarms = useMapStore((s) => s.alarms);
  const showOblastAlarms = useMapStore((s) => s.showOblastAlarms);
  const showTrajectories = useMapStore((s) => s.showTrajectories);
  const locateUserNonce = useMapStore((s) => s.locateUserNonce);
  const focusPlace = useMapStore((s) => s.focusPlace);
  const toggleTrajectoriesStore = useMapStore((s) => s.toggleTrajectories);

  useEffect(() => {
    if (!ProGate.isUnlockedSync(ProFeature.Trajectories, isPremium) && showTrajectories) {
      toggleTrajectoriesStore();
    }
  }, [isPremium, showTrajectories, toggleTrajectoriesStore]);

  const [follow, setFollow] = useState(false);
  const motionOverlay = useMarkerMotionOverlay();
  const { viewport, onRegionDidChange } = useMapViewportBounds();

  useEffect(() => {
    if (locateUserNonce > 0) {
      setFollow(true);
    }
  }, [locateUserNonce]);

  useEffect(() => {
    if (!focusPlace) return;
    setFollow(false);
    cameraRef.current?.setCamera({
      centerCoordinate: [focusPlace.lng, focusPlace.lat],
      zoomLevel: focusPlace.zoom ?? 12.5,
      animationMode: 'flyTo',
      animationDuration: focusPlace.duration ?? 1400,
    });
  }, [focusPlace]);

  const visibleMarkers = useMemo(() => {
    const filtered = markers.filter((marker) => visibleThreatTypes[marker.threatType] ?? true);
    const merged = mergeMotionIntoMarkers(filtered, motionOverlay);
    return cullMarkersForDisplay(merged, { viewport });
  }, [markers, visibleThreatTypes, motionOverlay, viewport]);
  const markerCollection = useMemo(() => markersToFeatureCollection(visibleMarkers), [visibleMarkers]);
  const trajectoryCollection = useMemo(
    () => (showTrajectories ? trajectoriesToFeatureCollection(visibleMarkers) : EMPTY_FEATURE_COLLECTION),
    [visibleMarkers, showTrajectories],
  );
  const oblastCollection = useMemo(
    () => (showOblastAlarms ? buildOblastAlarmGeoJson(alarms) : EMPTY_FEATURE_COLLECTION),
    [alarms, showOblastAlarms],
  );
  const districtAlarmCollection = useMemo(
    () => (showOblastAlarms ? buildDistrictAlarmGeoJson(alarms) : EMPTY_FEATURE_COLLECTION),
    [alarms, showOblastAlarms],
  );
  const districtBorderCollection = useMemo(
    () => (showOblastAlarms ? buildDistrictBorderGeoJson() : EMPTY_FEATURE_COLLECTION),
    [showOblastAlarms],
  );

  const hasActiveAlarms = useMemo(() => {
    if (!showOblastAlarms) return false;
    if (alarms.stateCount > 0 || alarms.districtCount > 0) return true;
    return (
      Object.values(alarms.stateAlarms).some(Boolean) ||
      Object.values(alarms.districtAlarms).some(Boolean)
    );
  }, [alarms, showOblastAlarms]);

  const alarmPulse = useAlarmPulse(hasActiveAlarms);
  const oblastFillOpacity = oblastPulseFillOpacity(alarmPulse);
  const districtFillOpacity = districtPulseFillOpacity(alarmPulse);

  return (
    <View style={styles.root}>
      <Mapbox.MapView
        style={StyleSheet.absoluteFill}
        styleJSON={mapStyleJson}
        compassEnabled
        logoEnabled={false}
        attributionEnabled={false}
        scaleBarEnabled={false}
        onRegionDidChange={onRegionDidChange}
      >
        <Mapbox.Camera
          ref={cameraRef}
          followUserLocation={follow}
          zoomLevel={AppConstants.defaultMapZoom}
          minZoomLevel={AppConstants.minMapZoom}
          maxZoomLevel={AppConstants.maxMapZoom}
          centerCoordinate={AppConstants.defaultMapCenter}
          animationMode="flyTo"
          animationDuration={550}
        />

        <Mapbox.ShapeSource id="district-borders" shape={districtBorderCollection}>
          <Mapbox.LineLayer
            id="district-border"
            style={{
              lineColor: 'rgba(255,255,255,0.08)',
              lineWidth: ['interpolate', ['linear'], ['zoom'], 7.5, 0.25, 11, 0.45],
              lineOpacity: ['step', ['zoom'], 0, 7.49, 0.08],
            }}
          />
        </Mapbox.ShapeSource>

        <Mapbox.ShapeSource id="district-alarms" shape={districtAlarmCollection}>
          <Mapbox.FillLayer
            id="district-fill"
            style={{
              fillColor: DISTRICT_ALARM_FILL,
              fillOpacity: districtFillOpacity,
            }}
          />
          <Mapbox.LineLayer
            id="district-alarm-outline"
            style={{
              lineColor: 'rgba(185,28,28,0.85)',
              lineWidth: 0.35,
              lineOpacity: 0.9,
            }}
          />
        </Mapbox.ShapeSource>

        <Mapbox.ShapeSource id="oblast-alarms" shape={oblastCollection}>
          <Mapbox.FillLayer
            id="oblast-fill"
            style={{
              fillColor: [
                'case',
                ['get', 'hasAlarm'],
                [
                  'match',
                  ['get', 'threatType'],
                  'raketa',
                  c.mapMissile,
                  'kab',
                  c.mapMissile,
                  'shahed',
                  c.mapDrone,
                  'fpv',
                  c.mapDrone,
                  'avia',
                  c.mapAviation,
                  c.mapAlarm,
                ],
                'rgba(0,0,0,0)',
              ],
              fillOpacity: ['case', ['get', 'hasAlarm'], oblastFillOpacity, 0],
            }}
          />
          <Mapbox.LineLayer
            id="oblast-outline"
            style={{
              lineColor: 'rgba(255,255,255,0.12)',
              lineWidth: 0.8,
            }}
          />
        </Mapbox.ShapeSource>

        <Mapbox.ShapeSource id="trajectories" shape={trajectoryCollection}>
          <Mapbox.LineLayer
            id="trajectory-line"
            style={{
              lineColor: ['case', ['get', 'predicted'], c.warning, c.accent2],
              lineWidth: 2,
              lineOpacity: 0.72,
              lineDasharray: [1.5, 1.1],
            }}
          />
        </Mapbox.ShapeSource>

        <Mapbox.ShapeSource id="threat-markers" shape={markerCollection} cluster clusterRadius={44} clusterMaxZoomLevel={8}>
          <Mapbox.CircleLayer
            id="clusters"
            filter={['has', 'point_count']}
            style={{
              circleColor: 'rgba(76,201,240,0.22)',
              circleStrokeColor: c.accent2,
              circleStrokeWidth: 1.5,
              circleRadius: ['step', ['get', 'point_count'], 18, 10, 23, 50, 30],
            }}
          />
          <Mapbox.SymbolLayer
            id="cluster-count"
            filter={['has', 'point_count']}
            style={{
              textField: ['get', 'point_count_abbreviated'],
              textColor: c.text,
              textSize: 12,
              textAllowOverlap: true,
            }}
          />
          <Mapbox.CircleLayer
            id="threat-glow"
            filter={['!', ['has', 'point_count']]}
            style={{
              circleRadius: 18,
              circleColor: [
                'match',
                ['get', 'threatType'],
                'raketa',
                c.mapMissile,
                'kab',
                c.mapMissile,
                'shahed',
                c.mapDrone,
                'fpv',
                c.mapDrone,
                'avia',
                c.mapAviation,
                c.mapFire,
              ],
              circleOpacity: 0.2,
              circleBlur: 0.85,
            }}
          />
          <Mapbox.CircleLayer
            id="threat-dot"
            filter={['!', ['has', 'point_count']]}
            style={{
              circleRadius: ['interpolate', ['linear'], ['zoom'], 4, 4, 8, 7, 11, 10],
              circleColor: [
                'match',
                ['get', 'threatType'],
                'raketa',
                c.mapMissile,
                'kab',
                c.mapMissile,
                'shahed',
                c.mapDrone,
                'fpv',
                c.mapDrone,
                'avia',
                c.mapAviation,
                c.mapFire,
              ],
              circleStrokeColor: '#fff',
              circleStrokeOpacity: 0.82,
              circleStrokeWidth: 1,
            }}
          />
          <Mapbox.SymbolLayer
            id="threat-count"
            filter={['all', ['!', ['has', 'point_count']], ['>', ['get', 'count'], 1]]}
            style={{
              textField: ['to-string', ['get', 'count']],
              textColor: '#07111C',
              textSize: 10,
              textAllowOverlap: true,
              textFont: Platform.OS === 'ios' ? ['Arial Unicode MS Bold'] : undefined,
            }}
          />
          <Mapbox.SymbolLayer
            id="threat-bearing"
            filter={['all', ['!', ['has', 'point_count']], ['>', ['get', 'bearing'], 0]]}
            style={{
              textField: '▲',
              textSize: 14,
              textColor: 'rgba(255,255,255,0.9)',
              textRotate: ['get', 'bearing'],
              textRotationAlignment: 'map',
              textAllowOverlap: true,
              textIgnorePlacement: true,
              textOffset: [0, -1.2],
            }}
          />
        </Mapbox.ShapeSource>
      </Mapbox.MapView>
    </View>
  );
}

function useMapStyles() {
  return useThemedStyles((t) =>
    StyleSheet.create({
      root: {
        flex: 1,
        backgroundColor: t.legacyColors.bg,
      },
    }),
  );
}
