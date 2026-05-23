import { Ionicons } from '@expo/vector-icons';
import { memo } from 'react';
import { StyleSheet } from 'react-native';
import { Text } from '../../../components/Text';
import { NeptunPressable } from '../../../design/components/NeptunPressable';
import { useAppTheme, useThemedStyles } from '../../../theme/useAppTheme';
import { fonts } from '../../../theme/fonts';
import { useProAccess } from '../hooks/useProAccess';
import { LOCKED_FEATURES, type LockedFeatureId } from '../utils/proFeatures';

type Props = {
  featureId: LockedFeatureId;
  source?: 'radar' | 'settings' | 'history';
};

function ProFeatureLockInner({ featureId, source = 'radar' }: Props) {
  const { theme } = useAppTheme();
  const { hasPlan, openPaywall } = useProAccess();
  const spec = LOCKED_FEATURES[featureId];
  const styles = useLockStyles();

  if (hasPlan(spec.minPlan)) {
    return null;
  }

  return (
    <NeptunPressable
      haptic
      scaleTo={0.97}
      onPress={() => openPaywall({ source, lockedFeature: featureId })}
      style={styles.chip}
    >
      <Ionicons name="lock-closed" size={13} color={theme.colors.textMuted} />
      <Text style={styles.label} numberOfLines={1}>
        {spec.label}
      </Text>
    </NeptunPressable>
  );
}

function useLockStyles() {
  return useThemedStyles((t) =>
    StyleSheet.create({
      chip: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 4,
        paddingHorizontal: 8,
        paddingVertical: 5,
        borderRadius: 6,
        borderWidth: StyleSheet.hairlineWidth,
        borderColor: t.colors.border,
        backgroundColor: t.colors.surfaceSoft,
      },
      label: {
        fontFamily: fonts.medium,
        fontSize: 11,
        color: t.colors.textSecondary,
        maxWidth: 120,
      },
    }),
  );
}

export const ProFeatureLock = memo(ProFeatureLockInner);
