import { useRouter } from 'expo-router';
import { memo, useCallback } from 'react';
import { StyleSheet, View } from 'react-native';
import { openNeptunTelegramChannel } from '../../../core/utils/openNeptunTelegram';
import { useProAccess } from '../../pro/hooks/useProAccess';
import { useMapStore } from '../state/mapStore';
import { MapLayerSheet } from './MapLayerSheet';
import { MapTabHeader } from './MapTabHeader';

function MapOverlayRootInner() {
  const router = useRouter();
  const { isPaid, openPaywall } = useProAccess();

  const openRadar = useCallback(() => router.push('/(tabs)/radar'), [router]);
  const openRegions = useCallback(() => router.push('/(tabs)/regions'), [router]);
  const openTelegram = useCallback(() => void openNeptunTelegramChannel('map_header'), []);

  return (
    <View style={StyleSheet.absoluteFill} pointerEvents="box-none">
      <MapTabHeader
        onStatusPress={openRadar}
        onRegionsPress={openRegions}
        onProPress={() => openPaywall({ source: 'map' })}
        onTelegramPress={openTelegram}
        isPaid={isPaid}
      />

      <MapLayerSheet />
    </View>
  );
}

export const MapOverlayRoot = memo(MapOverlayRootInner);
