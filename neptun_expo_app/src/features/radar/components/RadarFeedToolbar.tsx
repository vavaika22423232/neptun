import { memo } from 'react';
import { StyleSheet, View } from 'react-native';
import { useThemedStyles } from '../../../theme/useAppTheme';
import type { RadarQuickFilter } from '../domain/radarQuickFilter';
import { RadarFilterChips } from './RadarFilterChips';
import { RadarProUpsellRow } from './RadarProUpsellRow';
import { RadarSearchBar } from './RadarSearchBar';

type Props = {
  eventCount: number;
  historyMinutes: number;
  onlineCount: number;
  searchExpanded: boolean;
  searchQuery: string;
  recentSearches: string[];
  onToggleSearch: () => void;
  onSearchChange: (q: string) => void;
  onSearchSubmit: () => void;
  selectedFilter: RadarQuickFilter;
  onFilterChange: (f: RadarQuickFilter) => void;
  showMyRegions: boolean;
};

function RadarFeedToolbarInner(props: Props) {
  const styles = useRadarFeedToolbarStyles();

  return (
    <View style={styles.root}>
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
      <RadarProUpsellRow />
    </View>
  );
}

function useRadarFeedToolbarStyles() {
  return useThemedStyles((t) =>
    StyleSheet.create({
      root: {
        gap: 10,
        paddingBottom: 2,
      },
    }),
  );
}

export const RadarFeedToolbar = memo(RadarFeedToolbarInner);
