import { useState } from 'react';
import { Platform, StyleSheet, View } from 'react-native';
import { EmbedMapWebView } from '../features/map/components/EmbedMapWebView';
import { BallisticAllClearOverlay } from '../features/map/components/BallisticAllClearOverlay';
import { BallisticThreatOverlay } from '../features/map/components/BallisticThreatOverlay';
import { MapOverlayRoot } from '../features/map/components/MapOverlayRoot';
import { MapThreatMarkerSheet } from '../features/map/components/MapThreatMarkerSheet';
import { useBallisticMapOverlays } from '../features/map/hooks/useBallisticMapOverlays';
import { TacticalMap } from '../features/map/components/TacticalMap';
import { useLiveMapData } from '../features/map/hooks/useLiveMapData';
import { useThemedStyles } from '../theme/useAppTheme';

const MAP_ENGINE = (process.env.EXPO_PUBLIC_MAP_ENGINE ?? 'embed').toLowerCase();

export function MapScreen() {
  useLiveMapData(180);
  const styles = useThemedStyles((t) =>
    StyleSheet.create({
      root: {
        flex: 1,
        minHeight: 0,
        backgroundColor: t.colors.background,
        overflow: 'hidden',
      },
    }),
  );

  const [sheetRaw, setSheetRaw] = useState<Record<string, unknown> | null>(null);
  const ballistic = useBallisticMapOverlays();

  const showNative = MAP_ENGINE === 'native' && Platform.OS !== 'web';

  return (
    <View style={styles.root}>
      {showNative ? (
        <TacticalMap />
      ) : (
        <EmbedMapWebView onThreatMarkerTap={(marker) => setSheetRaw(marker)} />
      )}

      <MapOverlayRoot />

      {ballistic.threatVisible ? <BallisticThreatOverlay onDismiss={ballistic.dismissThreat} /> : null}
      {ballistic.allClearVisible ? (
        <BallisticAllClearOverlay
          progress={ballistic.allClearProgress}
          message={ballistic.region ? `Регіон: ${ballistic.region}` : undefined}
        />
      ) : null}

      <MapThreatMarkerSheet
        visible={sheetRaw != null}
        raw={sheetRaw}
        onClose={() => setSheetRaw(null)}
      />
    </View>
  );
}
