import { memo } from 'react';
import { StyleSheet, View } from 'react-native';
import { Text } from '../../../components/Text';
import { radarTheme } from '../constants/radarTheme';
import type { ConnectionStatus } from '../types/radar.types';
import type { RadarQuickFilter } from '../domain/radarQuickFilter';
import { fonts } from '../../../theme/fonts';
import { RadarFilterChips } from './RadarFilterChips';
import { RadarHeader } from './RadarHeader';
import { RadarSearchBar } from './RadarSearchBar';
import { RadarStaleBanner } from './RadarStaleBanner';
import { TelegramChannelCard } from './TelegramChannelCard';

export type RadarFeedHeaderProps = {
  connectionStatus: ConnectionStatus;
  eventCount: number;
  activeAlarms: number;
  lastFetchedLabel: string;
  showTelegramRow: boolean;
  onDismissTelegram: () => void;
  searchExpanded: boolean;
  searchQuery: string;
  recentSearches: string[];
  onToggleSearch: () => void;
  onSearchChange: (q: string) => void;
  onSearchSubmit: () => void;
  selectedFilter: RadarQuickFilter;
  onFilterChange: (f: RadarQuickFilter) => void;
  showMyRegions: boolean;
  historyMinutes: number;
  onlineCount: number;
  showStaleBanner: boolean;
};

function RadarFeedHeaderInner(props: RadarFeedHeaderProps) {
  return (
    <View style={styles.header}>
      <RadarHeader
        connectionStatus={props.connectionStatus}
        eventCount={props.eventCount}
        activeAlarms={props.activeAlarms}
        lastFetchedLabel={props.lastFetchedLabel}
      />
      <TelegramChannelCard
        compact={!props.showTelegramRow}
        onDismiss={props.onDismissTelegram}
      />
      <RadarSearchBar
        expanded={props.searchExpanded}
        query={props.searchQuery}
        recentSearches={props.recentSearches}
        onToggle={props.onToggleSearch}
        onChange={props.onSearchChange}
        onSubmit={props.onSearchSubmit}
      />
      <RadarFilterChips
        selected={props.selectedFilter}
        onChange={props.onFilterChange}
        showMyRegions={props.showMyRegions}
      />
      <Text style={styles.hint}>
        Вікно {props.historyMinutes} хв · онлайн {props.onlineCount > 0 ? props.onlineCount : '—'}
      </Text>
      {props.showStaleBanner ? <RadarStaleBanner /> : null}
    </View>
  );
}

export const RadarFeedHeader = memo(RadarFeedHeaderInner);

const styles = StyleSheet.create({
  header: { gap: radarTheme.cardGap, paddingBottom: radarTheme.sectionGap },
  hint: {
    fontFamily: fonts.medium,
    fontSize: 11,
    color: radarTheme.textMuted,
  },
});
