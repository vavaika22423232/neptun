import { Ionicons } from '@expo/vector-icons';
import type { ComponentProps, ReactNode } from 'react';
import { memo } from 'react';
import { StyleSheet, View } from 'react-native';
import { NeptunPressable } from '../../design/components/NeptunPressable';
import { useAppTheme, useThemedStyles } from '../../theme/useAppTheme';

type GroupProps = {
  children: ReactNode;
};

function NeptunTopBarActionGroupInner({ children }: GroupProps) {
  const styles = useGroupStyles();
  return <View style={styles.row}>{children}</View>;
}

type ButtonProps = {
  icon: ComponentProps<typeof Ionicons>['name'];
  onPress?: () => void;
  tone?: 'default' | 'accent' | 'warning' | 'premium';
  accessibilityLabel?: string;
};

function NeptunTopBarButtonInner({
  icon,
  onPress,
  tone = 'default',
  accessibilityLabel,
}: ButtonProps) {
  const { theme } = useAppTheme();
  const color =
    tone === 'accent'
      ? theme.colors.primary
      : tone === 'warning'
        ? theme.colors.warning
        : tone === 'premium'
          ? theme.colors.pro
          : theme.colors.textPrimary;

  return (
    <NeptunPressable
      haptic
      scaleTo={0.94}
      accessibilityLabel={accessibilityLabel}
      onPress={onPress}
      style={buttonStyles.btn}
    >
      <Ionicons name={icon} size={22} color={color} />
    </NeptunPressable>
  );
}

const buttonStyles = StyleSheet.create({
  btn: {
    width: 40,
    height: 40,
    alignItems: 'center',
    justifyContent: 'center',
  },
});

function useGroupStyles() {
  return useThemedStyles(() =>
    StyleSheet.create({
      row: {
        flexDirection: 'row',
        alignItems: 'center',
        marginRight: -4,
      },
    }),
  );
}

export const NeptunTopBarActionGroup = memo(NeptunTopBarActionGroupInner);
export const NeptunTopBarButton = memo(NeptunTopBarButtonInner);
