import { memo, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { RefreshControl, ScrollView, StyleSheet, View } from 'react-native';
import { useRouter } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { bottomNavOccupiedHeight } from '../../components/BottomNavigationBar';
import { useApp } from '../../context/AppContext';
import { NeptunEmptyState } from '../../design/components/NeptunEmptyState';
import { persistentStorage } from '../../services/persistentStorage';
import { PrefsKeys } from '../../config/prefsKeys';
import { useAppTheme, useThemedStyles } from '../../theme/useAppTheme';
import { RadarEmptyState } from '../../features/radar/components/RadarEmptyState';
import { RadarFeedCard } from '../../features/radar/components/RadarFeedCard';
import { RadarFeedToolbar } from '../../features/radar/components/RadarFeedToolbar';
import { RadarHistoryLink } from '../../features/radar/components/RadarHistoryLink';
import { RadarTelegramCard } from '../../features/radar/components/RadarTelegramCard';
import { RadarSectionHeader } from '../../features/radar/components/RadarSectionHeader';
import { RadarShimmerList } from '../../features/radar/components/RadarShimmerList';
import { RadarStaleBanner } from '../../features/radar/components/RadarStaleBanner';
import { ThreatDetailsSheet } from '../../features/radar/components/ThreatDetailsSheet';
import { ThreatEventCard } from '../../features/radar/components/ThreatEventCard';
import { useRadarFeedState } from '../../features/radar/hooks/useRadarFeedState';
import { useRadarStore } from '../../features/radar/store/radarStore';
import { buildRadarFeedRows } from '../../features/radar/utils/buildRadarSections';
import { buildThreatEvents } from '../../features/radar/utils/buildThreatEvents';
import type { RadarFeedRow } from '../../features/radar/types/radar.types';

export function RadarScreen() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const { theme } = useAppTheme();
  const styles = useRadarScreenStyles();
  const feed = useRadarFeedState();

  const { onlineCount } = useApp();
  const followedIds = useRadarStore((s) => s.followedIds);
  const mutedCategories = useRadarStore((s) => s.mutedCategories);
  const selectedEventId = useRadarStore((s) => s.selectedEventId);
  const selectedFilter = useRadarStore((s) => s.selectedFilter);
  const searchQuery = useRadarStore((s) => s.searchQuery);
  const searchExpanded = useRadarStore((s) => s.searchExpanded);
  const recentSearches = useRadarStore((s) => s.recentSearches);
  const hydrate = useRadarStore((s) => s.hydrate);
  const setFilter = useRadarStore((s) => s.setFilter);
  const setSearchQuery = useRadarStore((s) => s.setSearchQuery);
  const toggleSearch = useRadarStore((s) => s.toggleSearch);
  const addRecentSearch = useRadarStore((s) => s.addRecentSearch);
  const toggleFollow = useRadarStore((s) => s.toggleFollow);
  const toggleMuteCategory = useRadarStore((s) => s.toggleMuteCategory);
  const setSelectedEventId = useRadarStore((s) => s.setSelectedEventId);

  const scrollRef = useRef<ScrollView>(null);
  const [pullRefreshing, setPullRefreshing] = useState(false);

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  const myRegions = useMemo(
    () => persistentStorage.getStringList(PrefsKeys.selectedRegions),
    [feed.markers.length],
  );

  const events = useMemo(
    () =>
      buildThreatEvents(feed.markers, {
        filter: selectedFilter,
        searchQuery: searchQuery.trim() || undefined,
        myRegions,
        followedIds: new Set(followedIds),
        mutedCategories: new Set(mutedCategories),
      }),
    [feed.markers, selectedFilter, searchQuery, myRegions, followedIds, mutedCategories],
  );

  const rows = useMemo(() => buildRadarFeedRows(events), [events]);

  const selectedEvent = useMemo(
    () => events.find((e) => e.id === selectedEventId) ?? null,
    [events, selectedEventId],
  );

  const onRefresh = useCallback(async () => {
    setPullRefreshing(true);
    try {
      await feed.refetch();
    } finally {
      setPullRefreshing(false);
    }
  }, [feed.refetch]);

  const openMap = useCallback(() => {
    router.push('/(tabs)');
  }, [router]);

  const feedRows = useMemo(() => {
    if (rows.length === 0) {
      return null;
    }

    const lastEventRow = [...rows].reverse().find((r) => r.kind === 'event');
    const lastEventId = lastEventRow?.kind === 'event' ? lastEventRow.event.id : null;

    return (
      <RadarFeedCard>
        {rows.map((row) => (
          <RadarFeedRowView
            key={row.key}
            row={row}
            onOpen={setSelectedEventId}
            isLastInSection={row.kind === 'event' && row.event.id === lastEventId}
          />
        ))}
      </RadarFeedCard>
    );
  }, [rows, setSelectedEventId]);

  if (feed.isLoading) {
    return (
      <View style={styles.root}>
        <RadarShimmerList />
      </View>
    );
  }

  if (feed.error && feed.markers.length === 0) {
    return (
      <View style={styles.root}>
        <NeptunEmptyState
          icon="cloud-offline-outline"
          title="Помилка завантаження"
          subtitle="Перевірте з'єднання та спробуйте ще раз"
          actionLabel="Повторити"
          onAction={onRefresh}
        />
      </View>
    );
  }

  return (
    <View style={styles.root}>
      <ScrollView
        ref={scrollRef}
        style={styles.feed}
        contentContainerStyle={[
          styles.feedContent,
          { paddingBottom: bottomNavOccupiedHeight(insets.bottom) + 12 },
          rows.length === 0 ? styles.feedContentEmpty : null,
        ]}
        showsVerticalScrollIndicator={false}
        keyboardShouldPersistTaps="handled"
        bounces={false}
        overScrollMode="never"
        refreshControl={
          <RefreshControl
            refreshing={pullRefreshing}
            onRefresh={() => void onRefresh()}
            tintColor={theme.colors.primary}
          />
        }
      >
        {feed.showStaleBanner ? (
          <View style={styles.staleWrap}>
            <RadarStaleBanner />
          </View>
        ) : null}
        <RadarFeedToolbar
          eventCount={events.length}
          historyMinutes={feed.historyMinutes}
          onlineCount={onlineCount}
          searchExpanded={searchExpanded}
          searchQuery={searchQuery}
          recentSearches={recentSearches}
          onToggleSearch={toggleSearch}
          onSearchChange={setSearchQuery}
          onSearchSubmit={() => {
            if (searchQuery.trim()) addRecentSearch(searchQuery.trim());
          }}
          selectedFilter={selectedFilter}
          onFilterChange={setFilter}
          showMyRegions={myRegions.length > 0}
        />
        {rows.length === 0 ? (
          <RadarEmptyState lastFetchedAt={feed.lastFetchedAt} onOpenMap={openMap} />
        ) : (
          feedRows
        )}
        <View style={styles.footerGroup}>
          <RadarHistoryLink />
          <RadarTelegramCard />
        </View>
      </ScrollView>

      <ThreatDetailsSheet
        event={selectedEvent}
        visible={selectedEvent != null}
        onClose={() => setSelectedEventId(null)}
        onFollow={() => selectedEvent && toggleFollow(selectedEvent.id)}
        onMute={() => {
          if (selectedEvent) toggleMuteCategory(selectedEvent.id);
          setSelectedEventId(null);
        }}
      />
    </View>
  );
}

function useRadarScreenStyles() {
  return useThemedStyles((t) =>
    StyleSheet.create({
      root: { flex: 1, minHeight: 0, backgroundColor: t.radar.bg },
      feed: { flex: 1, minHeight: 0 },
      feedContent: {
        paddingHorizontal: t.radar.padH,
        paddingTop: 8,
        gap: t.radar.cardGap,
      },
      feedContentEmpty: {
        flexGrow: 1,
      },
      staleWrap: {},
      footerGroup: {
        gap: t.radar.cardGap,
      },
    }),
  );
}

const RadarFeedRowView = memo(function RadarFeedRowView({
  row,
  onOpen,
  isLastInSection,
}: {
  row: RadarFeedRow;
  onOpen: (id: string) => void;
  isLastInSection?: boolean;
}) {
  if (row.kind === 'section') {
    return <RadarSectionHeader title={row.title} />;
  }
  return <ThreatEventCard event={row.event} isLast={isLastInSection} onPress={() => onOpen(row.event.id)} />;
});
