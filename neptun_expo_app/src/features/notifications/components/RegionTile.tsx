import { Ionicons } from '@expo/vector-icons';
import { Pressable, StyleSheet, View } from 'react-native';
import { Text } from '../../../components/Text';
import { NeptunPressable } from '../../../design/components/NeptunPressable';
import { profileTokens } from '../../profile/profileTokens';
import { fonts } from '../../../theme/fonts';
import { useAppTheme, useThemedStyles } from '../../../theme/useAppTheme';

type Props = {
  name: string;
  emoji?: string;
  danger?: boolean;
  isSelected: boolean;
  isExpanded: boolean;
  districts?: string[];
  selectedDistricts: Set<string>;
  showDivider?: boolean;
  onOblastTap: () => void;
  onDistrictTap: (district: string) => void;
  onExpandTap?: () => void;
};

/** Oblast row inside grouped iOS-style list. */
export function RegionTile({
  name,
  emoji,
  danger,
  isSelected,
  isExpanded,
  districts,
  selectedDistricts,
  showDivider,
  onOblastTap,
  onDistrictTap,
  onExpandTap,
}: Props) {
  const { theme } = useAppTheme();
  const c = theme.colors;
  const styles = useTileStyles();
  const hasDistricts = (districts?.length ?? 0) > 0;
  const districtCount = selectedDistricts.size;
  const partialSelection = hasDistricts && districtCount > 0 && !isSelected;

  return (
    <View>
      <NeptunPressable
        haptic
        onPress={onOblastTap}
        style={[styles.oblastRow, (isSelected || partialSelection) && styles.oblastRowSelected]}
      >
        <View style={[styles.check, (isSelected || partialSelection) && styles.checkOn]}>
          {isSelected || partialSelection ? (
            <Ionicons
              name={partialSelection && !isSelected ? 'remove' : 'checkmark'}
              size={14}
              color={c.onAccent}
            />
          ) : null}
        </View>

        {emoji ? (
          <View style={styles.emojiPlate}>
            <Text style={styles.emoji}>{emoji}</Text>
          </View>
        ) : null}

        <View style={styles.copy}>
          <Text style={styles.name} numberOfLines={2}>
            {name}
          </Text>
          {hasDistricts ? (
            <Text style={styles.meta}>
              {districtCount > 0
                ? `${districtCount} з ${districts!.length} районів`
                : `${districts!.length} районів`}
            </Text>
          ) : null}
        </View>

        {danger ? <View style={styles.dangerDot} /> : null}

        {hasDistricts ? (
          <Pressable onPress={onExpandTap} hitSlop={10} style={styles.expandBtn}>
            <Ionicons name={isExpanded ? 'chevron-up' : 'chevron-down'} size={18} color={c.textFaint} />
          </Pressable>
        ) : null}
      </NeptunPressable>

      {isExpanded && hasDistricts ? (
        <View style={styles.districtBlock}>
          {districts!.map((district, index) => {
            const on = selectedDistricts.has(district);
            return (
              <View key={district}>
                <NeptunPressable
                  haptic
                  onPress={() => onDistrictTap(district)}
                  style={[styles.districtRow, on && styles.districtRowSelected]}
                >
                  <View style={[styles.checkSm, on && styles.checkOn]}>
                    {on ? <Ionicons name="checkmark" size={11} color={c.onAccent} /> : null}
                  </View>
                  <Text style={[styles.districtName, on && styles.districtNameOn]} numberOfLines={2}>
                    {district}
                  </Text>
                </NeptunPressable>
                {index < districts!.length - 1 ? <View style={styles.districtDivider} /> : null}
              </View>
            );
          })}
        </View>
      ) : null}

      {showDivider ? <View style={styles.divider} /> : null}
    </View>
  );
}

function useTileStyles() {
  return useThemedStyles((t) =>
    StyleSheet.create({
      oblastRow: {
        flexDirection: 'row',
        alignItems: 'center',
        minHeight: profileTokens.rowMinHeight + 4,
        paddingHorizontal: profileTokens.rowPadH,
        paddingVertical: profileTokens.rowPadV,
        gap: 12,
      },
      oblastRowSelected: {
        backgroundColor: t.colors.primaryMuted,
      },
      check: {
        width: 24,
        height: 24,
        borderRadius: 8,
        borderWidth: 2,
        borderColor: t.colors.borderStrong,
        alignItems: 'center',
        justifyContent: 'center',
      },
      checkSm: {
        width: 20,
        height: 20,
        borderRadius: 6,
        borderWidth: 1.5,
        borderColor: t.colors.borderStrong,
        alignItems: 'center',
        justifyContent: 'center',
      },
      checkOn: {
        backgroundColor: t.colors.primary,
        borderColor: t.colors.primary,
      },
      emojiPlate: {
        width: 32,
        height: 32,
        borderRadius: 10,
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: t.colors.surfaceSoft,
      },
      emoji: {
        fontSize: 18,
      },
      copy: {
        flex: 1,
        minWidth: 0,
        gap: 2,
      },
      name: {
        fontFamily: fonts.medium,
        fontSize: profileTokens.type.rowTitle.fontSize,
        lineHeight: profileTokens.type.rowTitle.lineHeight,
        color: t.colors.textPrimary,
      },
      meta: {
        fontFamily: fonts.regular,
        fontSize: profileTokens.type.rowSubtitle.fontSize,
        lineHeight: profileTokens.type.rowSubtitle.lineHeight,
        color: t.colors.textMuted,
      },
      dangerDot: {
        width: 8,
        height: 8,
        borderRadius: 4,
        backgroundColor: t.colors.warning,
      },
      expandBtn: {
        padding: 4,
      },
      districtBlock: {
        backgroundColor: t.colors.surfaceSoft,
        borderTopWidth: StyleSheet.hairlineWidth,
        borderTopColor: t.colors.divider,
        paddingLeft: profileTokens.rowPadH + 36,
        paddingRight: profileTokens.rowPadH,
        paddingBottom: 4,
      },
      districtRow: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 10,
        minHeight: 44,
        paddingVertical: 8,
      },
      districtRowSelected: {
        borderRadius: 10,
        paddingHorizontal: 8,
        marginHorizontal: -8,
        backgroundColor: t.colors.primaryMuted,
      },
      districtName: {
        flex: 1,
        fontFamily: fonts.regular,
        fontSize: 14,
        lineHeight: 18,
        color: t.colors.textSecondary,
      },
      districtNameOn: {
        fontFamily: fonts.medium,
        color: t.colors.textPrimary,
      },
      districtDivider: {
        height: StyleSheet.hairlineWidth,
        backgroundColor: t.colors.divider,
        marginLeft: 30,
      },
      divider: {
        height: StyleSheet.hairlineWidth,
        backgroundColor: t.colors.divider,
        marginLeft: profileTokens.rowPadH + profileTokens.iconColWidth + 12,
      },
    }),
  );
}
