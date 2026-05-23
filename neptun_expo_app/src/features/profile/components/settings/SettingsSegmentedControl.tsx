import { memo } from 'react';
import { StyleSheet, View } from 'react-native';
import { Text } from '../../../../components/Text';
import { NeptunPressable } from '../../../../design/components/NeptunPressable';
import { fonts } from '../../../../theme/fonts';
import { useThemedStyles } from '../../../../theme/useAppTheme';
import { profileTokens } from '../../profileTokens';

export type SegmentOption<T extends string> = {
  value: T;
  label: string;
};

type Props<T extends string> = {
  options: SegmentOption<T>[];
  value: T;
  onChange: (value: T) => void;
};

function SettingsSegmentedControlInner<T extends string>({ options, value, onChange }: Props<T>) {
  const styles = useSegmentStyles();
  return (
    <View style={styles.shell}>
      {options.map((opt) => {
        const active = opt.value === value;
        return (
          <NeptunPressable
            key={opt.value}
            haptic={false}
            onPress={() => onChange(opt.value)}
            style={[styles.segment, active && styles.segmentActive]}
          >
            <Text style={[styles.label, active && styles.labelActive]} numberOfLines={1}>
              {opt.label}
            </Text>
          </NeptunPressable>
        );
      })}
    </View>
  );
}

function useSegmentStyles() {
  return useThemedStyles((t) =>
    StyleSheet.create({
      shell: {
        flexDirection: 'row',
        height: 34,
        marginHorizontal: profileTokens.rowPadH,
        marginBottom: 12,
        padding: 3,
        borderRadius: t.radii.sm,
        backgroundColor: t.colors.surfaceSoft,
        borderWidth: StyleSheet.hairlineWidth,
        borderColor: t.colors.border,
      },
      segment: {
        flex: 1,
        alignItems: 'center',
        justifyContent: 'center',
        borderRadius: t.radii.xs,
      },
      segmentActive: {
        backgroundColor: t.colors.surfaceElevated,
        borderWidth: StyleSheet.hairlineWidth,
        borderColor: t.colors.borderStrong,
      },
      label: {
        fontFamily: fonts.medium,
        fontSize: 13,
        color: t.colors.textSecondary,
      },
      labelActive: {
        fontFamily: fonts.semiBold,
        color: t.colors.textPrimary,
      },
    }),
  );
}

export const SettingsSegmentedControl = memo(SettingsSegmentedControlInner) as typeof SettingsSegmentedControlInner;
