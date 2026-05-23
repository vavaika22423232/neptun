import type { ReactNode } from 'react';
import { memo } from 'react';
import { StyleSheet, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Text } from '../Text';
import { NeptunPressable } from '../../design/components/NeptunPressable';
import { useThemedStyles } from '../../theme/useAppTheme';
import { fonts } from '../../theme/fonts';

export type SimpleScreenHeaderProps = {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
  onTitlePress?: () => void;
};

function SimpleScreenHeaderInner({ title, subtitle, actions, onTitlePress }: SimpleScreenHeaderProps) {
  const insets = useSafeAreaInsets();
  const styles = useSimpleHeaderStyles();

  return (
    <View style={[styles.shell, { paddingTop: insets.top + 6 }]}>
      <View style={styles.bar}>
        <NeptunPressable
          haptic={false}
          scaleTo={0.99}
          style={styles.left}
          onPress={onTitlePress}
          disabled={!onTitlePress}
        >
          <Text style={styles.title}>{title}</Text>
          {subtitle ? (
            <Text style={styles.subtitle} numberOfLines={1}>
              {subtitle}
            </Text>
          ) : null}
        </NeptunPressable>
        {actions ? <View style={styles.actions}>{actions}</View> : null}
      </View>
    </View>
  );
}

function useSimpleHeaderStyles() {
  return useThemedStyles((t) =>
    StyleSheet.create({
      shell: {
        backgroundColor: t.colors.background,
        borderBottomWidth: StyleSheet.hairlineWidth,
        borderBottomColor: t.colors.border,
      },
      bar: {
        minHeight: 52,
        flexDirection: 'row',
        alignItems: 'center',
        paddingHorizontal: t.spacing.screenH,
        paddingBottom: 10,
        gap: 12,
      },
      left: { flex: 1, minWidth: 0, gap: 2 },
      title: {
        fontFamily: fonts.bold,
        fontSize: 24,
        letterSpacing: -0.3,
        color: t.colors.textPrimary,
      },
      subtitle: {
        fontFamily: fonts.medium,
        fontSize: 13,
        color: t.colors.textSecondary,
      },
      actions: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
        flexShrink: 0,
      },
    }),
  );
}

export const SimpleScreenHeader = memo(SimpleScreenHeaderInner);
