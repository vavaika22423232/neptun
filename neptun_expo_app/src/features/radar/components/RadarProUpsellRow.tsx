import { memo } from 'react';
import { ScrollView, StyleSheet } from 'react-native';
import { useProAccess } from '../../pro/hooks/useProAccess';
import { ProFeatureLock } from '../../pro/components/ProFeatureLock';
import { RADAR_PRO_CHIPS } from '../../pro/utils/proFeatures';

function RadarProUpsellRowInner() {
  const { isPaid } = useProAccess();

  if (isPaid) {
    return null;
  }

  return (
    <ScrollView
      horizontal
      showsHorizontalScrollIndicator={false}
      contentContainerStyle={styles.row}
      keyboardShouldPersistTaps="handled"
    >
      {RADAR_PRO_CHIPS.map((id) => (
        <ProFeatureLock key={id} featureId={id} source="radar" />
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  row: { gap: 6, paddingVertical: 0 },
});

export const RadarProUpsellRow = memo(RadarProUpsellRowInner);
