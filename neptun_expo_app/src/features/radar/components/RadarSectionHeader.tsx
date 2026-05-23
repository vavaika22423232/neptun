import { memo } from 'react';
import { StyleSheet, View } from 'react-native';
import { Text } from '../../../components/Text';
import { fonts } from '../../../theme/fonts';
import { useThemedStyles } from '../../../theme/useAppTheme';

type Props = { title: string };

function RadarSectionHeaderInner({ title }: Props) {
  const styles = useSectionStyles();

  return (
    <View style={styles.wrap}>
      <Text style={styles.title}>{title}</Text>
    </View>
  );
}

function useSectionStyles() {
  return useThemedStyles((t) =>
    StyleSheet.create({
      wrap: {
        paddingHorizontal: t.radar.cardPad,
        paddingTop: 14,
        paddingBottom: 6,
        backgroundColor: t.colors.card,
      },
      title: {
        fontFamily: fonts.semiBold,
        fontSize: 13,
        lineHeight: 18,
        color: t.colors.textMuted,
      },
    }),
  );
}

export const RadarSectionHeader = memo(RadarSectionHeaderInner);
