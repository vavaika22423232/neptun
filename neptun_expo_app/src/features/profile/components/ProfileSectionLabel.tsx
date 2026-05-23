import type { ComponentProps } from 'react';
import { StyleSheet, View } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { Text } from '../../../components/Text';
import { fonts } from '../../../theme/fonts';
import { useAppTheme, useThemedStyles } from '../../../theme/useAppTheme';

type Props = {
  title: string;
  icon?: ComponentProps<typeof Ionicons>['name'];
};

export function ProfileSectionLabel({ title, icon }: Props) {
  const { theme } = useAppTheme();
  const p = theme.profile;
  const styles = useThemedStyles((t) =>
    StyleSheet.create({
      row: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
        marginBottom: 8,
        marginTop: 2,
        paddingLeft: 4,
      },
      iconPlate: {
        width: 26,
        height: 26,
        borderRadius: 8,
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: t.profile.iconBg,
      },
      title: {
        fontFamily: fonts.semiBold,
        fontSize: 12,
        color: t.profile.sectionLabel,
        letterSpacing: 0.85,
        textTransform: 'uppercase',
      },
    }),
  );

  return (
    <View style={styles.row}>
      {icon ? (
        <View style={styles.iconPlate}>
          <Ionicons name={icon} size={14} color={p.textTertiary} />
        </View>
      ) : null}
      <Text style={styles.title}>{title}</Text>
    </View>
  );
}
