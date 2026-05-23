import type { ReactNode } from 'react';
import { memo } from 'react';
import { StyleSheet, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { NeptunPressable } from '../../design/components/NeptunPressable';
import { useThemedStyles } from '../../theme/useAppTheme';
import { fonts } from '../../theme/fonts';
import { AppText } from './AppText';

export type NeptunTopBarProps = {
  title: string;
  subtitle?: string;
  isLive?: boolean;
  actions?: ReactNode;
  onTitlePress?: () => void;
};

/** Compact native navigation bar — iOS-style inline title. */
function NeptunTopBarInner({ title, subtitle, actions, onTitlePress }: NeptunTopBarProps) {
  const insets = useSafeAreaInsets();
  const styles = useTopBarStyles();

  return (
    <View style={[styles.shell, { paddingTop: insets.top }]}>
      <View style={styles.bar}>
        <NeptunPressable
          haptic={false}
          scaleTo={0.99}
          style={styles.leading}
          onPress={onTitlePress}
          disabled={!onTitlePress}
        >
          <AppText variant="cardTitle" style={styles.title}>
            {title}
          </AppText>
          {subtitle ? (
            <AppText variant="meta" muted numberOfLines={1} style={styles.subtitle}>
              {subtitle}
            </AppText>
          ) : null}
        </NeptunPressable>
        {actions ? <View style={styles.actions}>{actions}</View> : null}
      </View>
    </View>
  );
}

function useTopBarStyles() {
  return useThemedStyles((t) =>
    StyleSheet.create({
      shell: {
        backgroundColor: t.colors.background,
        borderBottomWidth: StyleSheet.hairlineWidth,
        borderBottomColor: t.colors.border,
      },
      bar: {
        height: 44,
        flexDirection: 'row',
        alignItems: 'center',
        paddingHorizontal: t.spacing.screenH,
        gap: 8,
      },
      leading: { flex: 1, minWidth: 0, justifyContent: 'center', gap: 0 },
      title: {
        fontFamily: fonts.semiBold,
        fontSize: 17,
        letterSpacing: -0.2,
        lineHeight: 22,
      },
      subtitle: {
        fontFamily: fonts.regular,
        fontSize: 12,
        lineHeight: 16,
        marginTop: 1,
      },
      actions: {
        flexDirection: 'row',
        alignItems: 'center',
        flexShrink: 0,
      },
    }),
  );
}

export const NeptunTopBar = memo(NeptunTopBarInner);
