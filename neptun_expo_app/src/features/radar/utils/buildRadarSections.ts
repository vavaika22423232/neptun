import {
  RADAR_SECTION_TITLES,
  type RadarFeedRow,
  type RadarFeedSectionId,
  type ThreatEvent,
} from '../types/radar.types';

function appendSection(
  rows: RadarFeedRow[],
  sectionId: RadarFeedSectionId,
  events: ThreatEvent[],
): void {
  if (!events.length) return;
  rows.push({
    kind: 'section',
    key: `section-${sectionId}`,
    sectionId,
    title: RADAR_SECTION_TITLES[sectionId],
  });
  for (const event of events) {
    rows.push({ kind: 'event', key: `event-${event.id}`, event });
  }
}

/** Structured live feed: priority → active → new → watch. */
export function buildRadarFeedRows(events: ThreatEvent[]): RadarFeedRow[] {
  const visible = events.filter((e) => !e.isMuted);
  if (!visible.length) return [];

  const placed = new Set<string>();
  const take = (pred: (e: ThreatEvent) => boolean): ThreatEvent[] => {
    const batch = visible.filter((e) => !placed.has(e.id) && pred(e));
    batch.forEach((e) => placed.add(e.id));
    return batch;
  };

  const rows: RadarFeedRow[] = [];

  appendSection(
    rows,
    'highAttention',
    take((e) => e.severity === 'critical' || e.severity === 'high'),
  );
  appendSection(rows, 'newUpdates', take((e) => e.isNew));
  appendSection(rows, 'activeNow', take((e) => e.status === 'active'));
  appendSection(rows, 'recentlyEnded', take((e) => e.status === 'watch'));

  const rest = visible.filter((e) => !placed.has(e.id));
  if (rest.length) {
    appendSection(rows, 'activeNow', rest);
  }

  return rows;
}
