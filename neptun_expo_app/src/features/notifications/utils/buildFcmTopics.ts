import { DISTRICTS_BY_OBLAST, UKRAINE_OBLASTS } from '../../../data/ukraineRegions';
import { OBLAST_NAME_TO_ID } from '../constants/oblastIds';
import { regionToTopic } from './regionToTopic';

const OBLAST_NAMES = new Set(UKRAINE_OBLASTS.map((o) => o.name));
const TOTAL_OBLASTS = 25;

function oblastForDistrict(district: string): string | undefined {
  for (const [oblast, districts] of Object.entries(DISTRICTS_BY_OBLAST)) {
    if (districts.includes(district)) return oblast;
  }
  return undefined;
}

/** Resolve oblast display names to subscribe (districts → parent oblast). */
export function oblastNamesFromSelection(selected: string[]): Set<string> {
  const out = new Set<string>();
  for (const name of selected) {
    if (OBLAST_NAMES.has(name)) {
      out.add(name);
      continue;
    }
    const oblast = oblastForDistrict(name);
    if (oblast) out.add(oblast);
  }
  return out;
}

/** Flutter `updateRegions` topic set. */
export function buildFcmTopics(selectedRegions: string[]): string[] {
  const oblasts = oblastNamesFromSelection(selectedRegions);
  const topics = new Set<string>();
  for (const oblast of oblasts) {
    topics.add(regionToTopic(oblast));
  }
  const oblastCount = [...selectedRegions].filter((n) => OBLAST_NAMES.has(n)).length;
  if (oblastCount >= TOTAL_OBLASTS) {
    topics.add('all_regions');
  }
  return [...topics];
}

/** Persist `selected_oblast_ids` / `selected_raion_ids` for backend prefs API. */
export function persistRegionIdsFromSelection(selected: string[]): {
  oblastIds: string[];
  raionIds: string[];
} {
  const oblastIds = new Set<string>();
  const raionIds: string[] = [];
  for (const name of selected) {
    if (OBLAST_NAMES.has(name)) {
      const id = OBLAST_NAME_TO_ID[name];
      if (id) oblastIds.add(id);
    } else {
      raionIds.push(name);
      const oblast = oblastForDistrict(name);
      if (oblast) {
        const id = OBLAST_NAME_TO_ID[oblast];
        if (id) oblastIds.add(id);
      }
    }
  }
  return { oblastIds: [...oblastIds], raionIds };
}
