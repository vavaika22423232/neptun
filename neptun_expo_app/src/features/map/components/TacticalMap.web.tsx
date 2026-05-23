import { useMemo } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { colors } from '../../../theme/colors';
import { useLegacyScreenStyles } from '../../../theme/useLegacyScreenStyles';
import { Text } from '../../../components/Text';
import { useMapStore } from '../state/mapStore';

type Props = {
  onThreatMarkerTap?: (marker: Record<string, unknown>) => void;
};

/**
 * Web + `EXPO_PUBLIC_MAP_ENGINE=native` only — @rnmapbox/maps is native-only.
 * Default map tab uses EmbedMapWebView (same iframe as Flutter / iOS).
 */
export function TacticalMap(_props: Props) {
  const styles = useScreenStyles();
const markers = useMapStore((s) => s.markers);
  const visibleThreatTypes = useMapStore((s) => s.visibleThreatTypes);
  const linkPhase = useMapStore((s) => s.linkPhase);
  const alarms = useMapStore((s) => s.alarms);
  const visibleMarkers = useMemo(
    () => markers.filter((marker) => visibleThreatTypes[marker.threatType] ?? true),
    [markers, visibleThreatTypes],
  );

  return (
    <View style={styles.root}>
      <View style={styles.mapCore}>
        <Text style={styles.mapTitle}>NEPTUN Live Map</Text>
        <Text muted style={styles.mapSub}>
          Web preview uses the embedded live map. Native iOS/Android uses MapLibre rendering.
        </Text>
        <Text muted style={styles.mapSub}>
          {linkPhase === 'live' ? 'LIVE' : linkPhase} · {alarms.stateCount} обл. · {visibleMarkers.length} марк.
        </Text>
      </View>
      <View pointerEvents="box-none" style={styles.overlay}>
        <View style={styles.controls}>
          <Pressable style={styles.control}>
            <Ionicons name="navigate-outline" color={colors.text} size={20} />
          </Pressable>
        </View>
      </View>
    </View>
  );
}


function useScreenStyles() {
  return useLegacyScreenStyles((c) => ({
  root: {
    flex: 1,
    overflow: 'hidden',
    backgroundColor: c.bg,
  },
  mapCore: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 24,
    gap: 8,
  },
  mapTitle: {
    fontSize: 18,
    fontWeight: '800',
  },
  mapSub: {
    fontSize: 12,
    textAlign: 'center',
  },
  overlay: {
    ...StyleSheet.absoluteFillObject,
    padding: 14,
    justifyContent: 'flex-end',
  },
  controls: {
    alignSelf: 'flex-end',
    gap: 8,
  },
  control: {
    width: 42,
    height: 42,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'rgba(7,10,18,0.78)',
    borderWidth: StyleSheet.hairlineWidth,
    borderColor: c.borderStrong,
  },
}));
}
