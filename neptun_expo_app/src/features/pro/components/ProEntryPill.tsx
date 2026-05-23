import { Ionicons } from '@expo/vector-icons';
import { memo } from 'react';
import { StyleSheet } from 'react-native';
import { Text } from '../../../components/Text';
import { NeptunPressable } from '../../../design/components/NeptunPressable';
import { useAppTheme, useThemedStyles } from '../../../theme/useAppTheme';
import { fonts } from '../../../theme/fonts';
import type { ProEntrySource } from '../utils/proFeatures';

export type ProEntryPillProps = {
  compact?: boolean;
  source?: ProEntrySource;
  label?: string;
  onPress: () => void;
};

function ProEntryPillInner({ compact = true, label = 'PRO', onPress }: ProEntryPillProps) {
  const { theme } = useAppTheme();
  const styles = useProPillStyles();
  const h = compact ? 40 : 42;

  return (
    <NeptunPressable
      haptic
      scaleTo={0.94}
      accessibilityLabel="Відкрити PRO"
      onPress={onPress}
      style={[
        styles.pill,
        {
          height: h,
          backgroundColor: theme.colors.proSoft,
          borderColor: theme.colors.pro + '44',
        },
      ]}
    >
      <Ionicons name="sparkles" size={compact ? 16 : 18} color={theme.colors.pro} />
      <Text style={[styles.text, { color: theme.colors.premiumDeep }]}>{label}</Text>
    </NeptunPressable>
  );
}

function useProPillStyles() {
  return useThemedStyles(() =>
    StyleSheet.create({
      pill: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 5,
        paddingHorizontal: 12,
        borderRadius: 999,
        borderWidth: StyleSheet.hairlineWidth,
      },
      text: {
        fontFamily: fonts.semiBold,
        fontSize: 13,
        letterSpacing: 0.2,
      },
    }),
  );
}

export const ProEntryPill = memo(ProEntryPillInner);
