import { OBLAST_NAME_TO_ID } from '../../notifications/constants/oblastIds';
import { oblastNamesFromSelection } from '../../notifications/utils/buildFcmTopics';

/** Flutter `aggregateHeatmapCountsByStateId`. */
export function aggregateHeatmapCountsByStateId(
  mergedCountsByDisplayName: Record<string, number>,
): Record<string, number> {
  const out: Record<string, number> = {};

  for (const [name, count] of Object.entries(mergedCountsByDisplayName)) {
    const trimmed = name.trim();
    if (!trimmed || count <= 0) continue;

    let stateId = OBLAST_NAME_TO_ID[trimmed];
    if (!stateId) {
      const oblasts = oblastNamesFromSelection([trimmed]);
      const parent = [...oblasts][0];
      if (parent) stateId = OBLAST_NAME_TO_ID[parent];
    }
    if (!stateId) continue;
    out[stateId] = (out[stateId] ?? 0) + count;
  }

  return out;
}
