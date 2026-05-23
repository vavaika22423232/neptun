import { Ionicons } from '@expo/vector-icons';
import { Pressable, StyleSheet, TextInput, View, type TextInputProps } from 'react-native';
import { radii, spacing } from '../tokens';
import { fonts } from '../../theme/fonts';
import { useAppTheme, useThemedStyles } from '../../theme/useAppTheme';

type Props = TextInputProps & {
  onClear?: () => void;
};

export function NeptunSearchField({ value, onChangeText, onClear, style, ...rest }: Props) {
  const { theme } = useAppTheme();
  const c = theme.colors;
  const styles = useThemedStyles((t) =>
    StyleSheet.create({
      wrap: {
        flexDirection: 'row',
        alignItems: 'center',
        minHeight: 46,
        borderRadius: radii.lg,
        backgroundColor: t.colors.input,
        borderWidth: StyleSheet.hairlineWidth,
        borderColor: t.colors.border,
        paddingHorizontal: spacing.md,
        ...t.shadows.sm,
      },
      icon: { marginRight: spacing.sm },
      input: {
        flex: 1,
        color: t.colors.textPrimary,
        fontFamily: fonts.medium,
        fontSize: 15,
        paddingVertical: spacing.sm,
      },
      clear: { marginLeft: spacing.xs },
    }),
  );

  const showClear = typeof value === 'string' && value.length > 0;
  return (
    <View style={styles.wrap}>
      <Ionicons name="search" size={18} color={c.textMuted} style={styles.icon} />
      <TextInput
        {...rest}
        value={value}
        onChangeText={onChangeText}
        placeholderTextColor={c.textFaint}
        style={[styles.input, style]}
      />
      {showClear && onClear ? (
        <Pressable onPress={onClear} hitSlop={8} style={styles.clear}>
          <Ionicons name="close-circle" size={18} color={c.textMuted} />
        </Pressable>
      ) : null}
    </View>
  );
}
