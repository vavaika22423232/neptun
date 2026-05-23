import { Ionicons } from '@expo/vector-icons';
import { useCallback, useState } from 'react';
import {
  ActivityIndicator,
  RefreshControl,
  ScrollView,
  StyleSheet,
  View,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { bottomNavOccupiedHeight } from '../components/BottomNavigationBar';
import { Text } from '../components/Text';
import { NeptunEmptyState } from '../design/components/NeptunEmptyState';
import { NeptunPressable } from '../design/components/NeptunPressable';
import { NeptunSearchField } from '../design/components/NeptunSearchField';
import { districtsForOblast } from '../data/ukraineRegions';
import { RegionTile } from '../features/notifications/components/RegionTile';
import { RegionsSummaryCard } from '../features/notifications/components/RegionsSummaryCard';
import { useRegionSelection } from '../features/notifications/hooks/useRegionSelection';
import { profileTokens } from '../features/profile/profileTokens';
import { fonts } from '../theme/fonts';
import { useAppTheme, useThemedStyles } from '../theme/useAppTheme';

/** Flutter `AlertsPage` / `messages_page.dart` — region push subscriptions */
export function RegionsScreen() {
  const { theme } = useAppTheme();
  const [refreshing, setRefreshing] = useState(false);
  const styles = useScreenStyles();

  const {
    loading,
    selected,
    expandedOblast,
    setExpandedOblast,
    searchQuery,
    setSearchQuery,
    filteredOblasts,
    selectedOblastCount,
    toggleOblast,
    toggleDistrict,
    selectAll,
    clearAll,
    reload,
  } = useRegionSelection();

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    try {
      await reload();
    } finally {
      setRefreshing(false);
    }
  }, [reload]);

  if (loading) {
    return (
      <View style={styles.root}>
        <ActivityIndicator color={theme.colors.primary} style={styles.loader} />
      </View>
    );
  }

  return (
    <View style={styles.root}>
      <ScrollView
        contentContainerStyle={styles.scroll}
        showsVerticalScrollIndicator={false}
        keyboardShouldPersistTaps="handled"
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={() => void onRefresh()}
            tintColor={theme.colors.primary}
          />
        }
      >
        <RegionsSummaryCard selectedCount={selected.size} oblastCount={selectedOblastCount} />

        <View style={styles.toolsCard}>
          <NeptunSearchField
            value={searchQuery}
            onChangeText={setSearchQuery}
            placeholder="Пошук області чи району"
            onClear={() => setSearchQuery('')}
          />

          <View style={styles.toolsDivider} />

          <View style={styles.toolsRow}>
            <NeptunPressable haptic style={styles.toolBtn} onPress={selectAll}>
              <Ionicons name="checkmark-done-outline" size={18} color={theme.colors.primary} />
              <Text style={styles.toolBtnLabelPrimary}>Обрати всі</Text>
            </NeptunPressable>

            <View style={styles.toolsSplit} />

            <NeptunPressable haptic style={styles.toolBtn} onPress={clearAll}>
              <Ionicons name="close-circle-outline" size={18} color={theme.colors.textMuted} />
              <Text style={styles.toolBtnLabel}>Скинути</Text>
            </NeptunPressable>
          </View>
        </View>

        <View style={styles.sectionHead}>
          <Text style={styles.sectionTitle}>Області України</Text>
          <Text style={styles.sectionSubtitle}>
            Натисніть область, щоб розгорнути райони. Зміни зберігаються автоматично.
          </Text>
        </View>

        {filteredOblasts.length === 0 ? (
          <View style={styles.listCard}>
            <NeptunEmptyState
              icon="search-outline"
              title="Нічого не знайдено"
              subtitle="Спробуйте інший запит або скиньте пошук"
              actionLabel="Очистити пошук"
              onAction={() => setSearchQuery('')}
            />
          </View>
        ) : (
          <View style={styles.listCard}>
            {filteredOblasts.map((oblast, index) => {
              const districts = districtsForOblast(oblast.name);
              const isExpanded = expandedOblast === oblast.name;
              const selectedDistricts = new Set(districts.filter((d) => selected.has(d)));

              return (
                <RegionTile
                  key={oblast.name}
                  name={oblast.name}
                  emoji={oblast.icon}
                  danger={oblast.danger}
                  isSelected={selected.has(oblast.name)}
                  isExpanded={isExpanded}
                  districts={districts}
                  selectedDistricts={selectedDistricts}
                  showDivider={index < filteredOblasts.length - 1}
                  onOblastTap={() => {
                    if (isExpanded) toggleOblast(oblast.name);
                    else setExpandedOblast(oblast.name);
                  }}
                  onDistrictTap={(d) => toggleDistrict(d, oblast.name)}
                  onExpandTap={() => setExpandedOblast(isExpanded ? null : oblast.name)}
                />
              );
            })}
          </View>
        )}
      </ScrollView>
    </View>
  );
}

function useScreenStyles() {
  const insets = useSafeAreaInsets();
  return useThemedStyles((t) =>
    StyleSheet.create({
      root: {
        flex: 1,
        backgroundColor: t.colors.cardMuted,
      },
      loader: {
        marginTop: 48,
      },
      scroll: {
        paddingTop: 8,
        paddingBottom: bottomNavOccupiedHeight(insets.bottom) + 16,
        gap: profileTokens.groupGap,
      },
      toolsCard: {
        marginHorizontal: profileTokens.insetH,
        padding: profileTokens.rowPadH,
        borderRadius: profileTokens.cardRadius,
        backgroundColor: t.colors.card,
        gap: 12,
        shadowColor: '#000',
        shadowOpacity: t.scheme === 'light' ? 0.04 : 0,
        shadowRadius: 8,
        shadowOffset: { width: 0, height: 2 },
        elevation: t.scheme === 'light' ? 1 : 0,
      },
      toolsDivider: {
        height: StyleSheet.hairlineWidth,
        backgroundColor: t.colors.divider,
      },
      toolsRow: {
        flexDirection: 'row',
        alignItems: 'center',
      },
      toolBtn: {
        flex: 1,
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 8,
        paddingVertical: 10,
        borderRadius: 12,
      },
      toolBtnLabelPrimary: {
        fontFamily: fonts.semiBold,
        fontSize: 14,
        color: t.colors.primary,
      },
      toolBtnLabel: {
        fontFamily: fonts.semiBold,
        fontSize: 14,
        color: t.colors.textSecondary,
      },
      toolsSplit: {
        width: StyleSheet.hairlineWidth,
        alignSelf: 'stretch',
        backgroundColor: t.colors.divider,
      },
      sectionHead: {
        gap: 4,
        paddingHorizontal: profileTokens.insetH + 4,
      },
      sectionTitle: {
        fontFamily: fonts.semiBold,
        fontSize: profileTokens.type.sectionLabel.fontSize,
        lineHeight: profileTokens.type.sectionLabel.lineHeight,
        color: t.colors.textPrimary,
      },
      sectionSubtitle: {
        fontFamily: fonts.regular,
        fontSize: profileTokens.type.rowSubtitle.fontSize,
        lineHeight: profileTokens.type.rowSubtitle.lineHeight,
        color: t.colors.textMuted,
      },
      listCard: {
        marginHorizontal: profileTokens.insetH,
        borderRadius: profileTokens.cardRadius,
        backgroundColor: t.colors.card,
        overflow: 'hidden',
        shadowColor: '#000',
        shadowOpacity: t.scheme === 'light' ? 0.04 : 0,
        shadowRadius: 8,
        shadowOffset: { width: 0, height: 2 },
        elevation: t.scheme === 'light' ? 1 : 0,
      },
    }),
  );
}
