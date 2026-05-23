import AsyncStorage from '@react-native-async-storage/async-storage';
import type { RadarSnapshot } from '../domain/radarSnapshot';

const CACHE_KEY = 'neptun_radar_snapshot_v1';

export const radarSnapshotCache = {
  async save(snapshot: RadarSnapshot): Promise<void> {
    await AsyncStorage.setItem(CACHE_KEY, JSON.stringify(snapshot));
  },

  async load(): Promise<RadarSnapshot | null> {
    const raw = await AsyncStorage.getItem(CACHE_KEY);
    if (!raw) return null;
    try {
      const parsed = JSON.parse(raw) as RadarSnapshot;
      if (!Array.isArray(parsed.markers)) return null;
      return { ...parsed, fromDiskCache: true };
    } catch {
      return null;
    }
  },
};
