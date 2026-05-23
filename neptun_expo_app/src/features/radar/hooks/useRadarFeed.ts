import { useQuery } from '@tanstack/react-query';
import { useMemo, useState } from 'react';
import type { RadarQuickFilter } from '../domain/radarQuickFilter';
import { radarRepository } from '../data/radarRepository';
import { buildRadarFeedListItems, buildSortedRadarFeedEntries } from '../logic/buildRadarFeed';

const HISTORY_MINUTES = 180;

export function useRadarFeed() {
  const [filter, setFilter] = useState<RadarQuickFilter>('all');

  const query = useQuery({
    queryKey: ['radar', 'snapshot', HISTORY_MINUTES],
    queryFn: () => radarRepository.fetchSnapshot(HISTORY_MINUTES),
    staleTime: 20_000,
    refetchInterval: 30_000,
  });

  const listItems = useMemo(() => {
    const markers = query.data?.markers ?? [];
    const sorted = buildSortedRadarFeedEntries(markers, filter);
    return buildRadarFeedListItems(sorted);
  }, [query.data?.markers, filter]);

  return {
    filter,
    setFilter,
    listItems,
    activeAlarms: query.data?.activeOblastsUnderAlarm ?? 0,
    fromDiskCache: query.data?.fromDiskCache ?? false,
    isLoading: query.isLoading,
    isError: query.isError,
    refetch: query.refetch,
  };
}
