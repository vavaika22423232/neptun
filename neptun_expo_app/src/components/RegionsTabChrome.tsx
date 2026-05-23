import { useFocusEffect } from '@react-navigation/native';
import { memo, useCallback, useMemo } from 'react';
import { View } from 'react-native';
import { useProfileSettings } from '../features/profile/hooks/useProfileSettings';
import { regionSelectionLabel } from '../features/profile/utils/regionSelectionLabel';
import { OfflineBanner } from './OfflineBanner';
import { TabScreenHeader } from './ui/TabScreenHeader';

function RegionsTabChromeInner() {
  const settings = useProfileSettings();

  useFocusEffect(
    useCallback(() => {
      settings.reload();
    }, [settings.reload]),
  );

  const subtitle = useMemo(
    () => regionSelectionLabel(settings.regionSelectionCount),
    [settings.regionSelectionCount],
  );

  return (
    <View>
      <TabScreenHeader title="Регіони" subtitle={subtitle} />
      <OfflineBanner />
    </View>
  );
}

export const RegionsTabChrome = memo(RegionsTabChromeInner);
