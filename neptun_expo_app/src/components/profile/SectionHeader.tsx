import { Ionicons } from '@expo/vector-icons';
import { StyleSheet, View } from 'react-native';
import { Text } from '../Text';
import { colors } from '../../theme/colors';
import { fonts } from '../../theme/fonts';
import { spacing } from '../../theme/colors';
import { useLegacyScreenStyles } from '../../theme/useLegacyScreenStyles';

type Props = {
  title: string;
  icon: React.ComponentProps<typeof Ionicons>['name'];
};

export function SectionHeader({ title, icon }: Props) {
  const styles = useScreenStyles();
  return (
    <View style={styles.row}>
      <Ionicons name={icon} size={18} color={colors.muted} />
      <Text style={styles.title}>{title}</Text>
    </View>
  );
}


function useScreenStyles() {
  return useLegacyScreenStyles((c) => ({
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginTop: spacing.xl,
    marginBottom: spacing.sm,
    paddingLeft: spacing.xs,
  },
  title: {
    fontFamily: fonts.semiBold,
    fontSize: 14,
    color: c.muted,
    letterSpacing: 0.5,
  },
}));
}
