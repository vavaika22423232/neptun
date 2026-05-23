import { memo, useMemo } from 'react';
import { StyleSheet, View } from 'react-native';
import { useAppTheme } from '../../../theme/useAppTheme';
import { mapOverlayTokens } from './mapOverlayTokens';
import { MapControlButton } from './MapControlButton';

export type MapControlsClusterProps = {
  onLocationPress?: () => void;
  onNotificationsPress?: () => void;
  onLayersPress?: () => void;
  onMorePress?: () => void;
};

function MapControlsClusterInner({
  onLocationPress,
  onNotificationsPress,
  onLayersPress,
  onMorePress,
}: MapControlsClusterProps) {
  const { theme } = useAppTheme();
  const tokens = useMemo(() => mapOverlayTokens(theme.scheme), [theme.scheme]);
  const iconColor = tokens.textSecondary;

  return (
    <View
      style={[
        styles.capsule,
        { backgroundColor: tokens.bg, borderColor: tokens.border },
      ]}
    >
      <MapControlButton
        icon="locate-outline"
        label="Моє місце"
        color={iconColor}
        onPress={() => onLocationPress?.()}
      />
      <MapControlButton
        icon="notifications-outline"
        label="Сповіщення"
        color={iconColor}
        onPress={() => onNotificationsPress?.()}
      />
      <MapControlButton
        icon="layers-outline"
        label="Шари"
        color={iconColor}
        onPress={() => onLayersPress?.()}
      />
      <MapControlButton
        icon="ellipsis-horizontal"
        label="Ще"
        color={iconColor}
        onPress={() => onMorePress?.()}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  capsule: {
    flexDirection: 'row',
    alignItems: 'center',
    height: 46,
    paddingHorizontal: 4,
    borderRadius: 999,
    borderWidth: StyleSheet.hairlineWidth,
  },
});

export const MapControlsCluster = memo(MapControlsClusterInner);
