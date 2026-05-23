import { create } from 'zustand';
import { PrefsKeys } from '../../../config/prefsKeys';
import { persistentStorage } from '../../../services/persistentStorage';
import { RADAR_FILTER_LABELS, type RadarQuickFilter } from '../domain/radarQuickFilter';

type RadarStore = {
  selectedFilter: RadarQuickFilter;
  searchQuery: string;
  searchExpanded: boolean;
  unreadCount: number;
  followedIds: string[];
  mutedCategories: string[];
  recentSearches: string[];
  selectedEventId: string | null;

  hydrate: () => void;
  setFilter: (f: RadarQuickFilter) => void;
  setSearchQuery: (q: string) => void;
  toggleSearch: () => void;
  addRecentSearch: (q: string) => void;
  bumpUnread: (n: number) => void;
  clearUnread: () => void;
  toggleFollow: (id: string) => void;
  toggleMuteCategory: (id: string) => void;
  setSelectedEventId: (id: string | null) => void;
};

function loadList(key: string): string[] {
  return persistentStorage.getStringList(key);
}

function saveList(key: string, values: string[]) {
  persistentStorage.setStringList(key, values);
}

function isRadarFilter(v: string | undefined): v is RadarQuickFilter {
  return v != null && v in RADAR_FILTER_LABELS;
}

export const useRadarStore = create<RadarStore>((set, get) => ({
  selectedFilter: 'all',
  searchQuery: '',
  searchExpanded: false,
  unreadCount: 0,
  followedIds: [],
  mutedCategories: [],
  recentSearches: [],
  selectedEventId: null,

  hydrate() {
    const raw = persistentStorage.getString(PrefsKeys.radarSelectedFilter);
    set({
      selectedFilter: isRadarFilter(raw) ? raw : 'all',
      followedIds: loadList(PrefsKeys.radarFollowedIds),
      mutedCategories: loadList(PrefsKeys.radarMutedCategories),
      recentSearches: loadList(PrefsKeys.radarRecentSearches).slice(0, 12),
    });
  },

  setFilter(f) {
    persistentStorage.setString(PrefsKeys.radarSelectedFilter, f);
    set({ selectedFilter: f });
  },

  setSearchQuery(q) {
    set({ searchQuery: q });
  },

  toggleSearch() {
    set((s) => ({ searchExpanded: !s.searchExpanded }));
  },

  addRecentSearch(q) {
    const trimmed = q.trim();
    if (trimmed.length < 2) return;
    const next = [trimmed, ...get().recentSearches.filter((x) => x !== trimmed)].slice(0, 8);
    saveList(PrefsKeys.radarRecentSearches, next);
    set({ recentSearches: next });
  },

  bumpUnread(n) {
    set((s) => ({ unreadCount: s.unreadCount + n }));
  },

  clearUnread() {
    set({ unreadCount: 0 });
  },

  toggleFollow(id) {
    const ids = new Set(get().followedIds);
    if (ids.has(id)) ids.delete(id);
    else ids.add(id);
    const arr = [...ids];
    saveList(PrefsKeys.radarFollowedIds, arr);
    set({ followedIds: arr });
  },

  toggleMuteCategory(id) {
    const ids = new Set(get().mutedCategories);
    if (ids.has(id)) ids.delete(id);
    else ids.add(id);
    const arr = [...ids];
    saveList(PrefsKeys.radarMutedCategories, arr);
    set({ mutedCategories: arr });
  },

  setSelectedEventId(id) {
    set({ selectedEventId: id });
  },
}));
