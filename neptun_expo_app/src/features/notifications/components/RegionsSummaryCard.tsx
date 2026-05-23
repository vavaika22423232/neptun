import { Ionicons } from '@expo/vector-icons';
import { memo } from 'react';
import { StyleSheet, View } from 'react-native';
import { Text } from '../../../components/Text';
import { regionSelectionLabel } from '../../profile/utils/regionSelectionLabel';
import { profileTokens } from '../../profile/profileTokens';
import { fonts } from '../../../theme/fonts';
import { useThemedStyles } from '../../../theme/useAppTheme';

type Props = {
  selectedCount: number;
  oblastCount: number;
};

function RegionsSummaryCardInner({ selectedCount, oblastCount }: Props) {
  const styles = useCardStyles();
  const title = regionSelectionLabel(selectedCount);
  const oblastPart =
    oblastCount === 0
      ? 'Області не обрані'
      : oblastCount === 1
        ? '1 область'
        : oblastCount < 5
          ? `${oblastCount} області`
          : `${oblastCount} областей`;

  return (
    <View style={styles.card}>
      <View style={styles.row}>
        <View style={styles.iconPlate}>
          <Ionicons name="notifications" size={22} color="#FFFFFF" />
        </View>
        <View style={styles.copy}>
          <Text style={styles.title}>{title}</Text>
          <Text style={styles.subtitle}>
            {oblastPart} · підписки оновлюються автоматично
          </Text>
        </View>
        {selectedCount > 0 ? (
          <View style={styles.countBadge}>
            <Text style={styles.countText}>{selectedCount}</Text>
          </View>
        ) : null}
      </View>
    </View>
  );
}

function useCardStyles() {
  return useThemedStyles((t) =>
    StyleSheet.create({
      card: {
        marginHorizontal: profileTokens.insetH,
        padding: profileTokens.statusCardPad,
        borderRadius: profileTokens.cardRadius,
        backgroundColor: t.colors.card,
        shadowColor: '#000',
        shadowOpacity: t.scheme === 'light' ? 0.04 : 0,
        shadowRadius: 8,
        shadowOffset: { width: 0, height: 2 },
        elevation: t.scheme === 'light' ? 1 : 0,
      },
      row: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 14,
      },
      iconPlate: {
        width: profileTokens.avatarSize,
        height: profileTokens.avatarSize,
        borderRadius: 16,
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: t.colors.primary,
      },
      copy: {
        flex: 1,
        minWidth: 0,
        gap: 4,
      },
      title: {
        fontFamily: fonts.semiBold,
        fontSize: profileTokens.type.accountTitle.fontSize,
        color: t.colors.textPrimary,
      },
      subtitle: {
        fontFamily: fonts.regular,
        fontSize: profileTokens.type.rowSubtitle.fontSize,
        lineHeight: profileTokens.type.rowSubtitle.lineHeight,
        color: t.colors.textMuted,
      },
      countBadge: {
        minWidth: 32,
        height: 32,
        paddingHorizontal: 10,
        borderRadius: 16,
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: t.colors.primaryMuted,
      },
      countText: {
        fontFamily: fonts.bold,
        fontSize: 15,
        color: t.colors.primary,
      },
    }),
  );
}

export const RegionsSummaryCard = memo(RegionsSummaryCardInner);
