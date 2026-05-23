import type { RadarQuickFilter } from '../domain/radarQuickFilter';
import { radarFilterMatchesMarker } from '../domain/radarQuickFilter';
import { radarThreatTypeLabel } from '../domain/radarThreatLabel';

export type RadarFeedEntry = {
  raw: Record<string, unknown>;
  sortKey: number | null;
  place: string;
  typeKey: string;
  typeLabel: string;
  displayTime: string;
};

export type RadarListItem =
  | { kind: 'section'; title: string }
  | { kind: 'row'; entry: RadarFeedEntry };

function radarMarkerTimestamp(m: Record<string, unknown>): number | null {
  const dateStr = String(m.date ?? m.timestamp ?? '');
  const t = Date.parse(dateStr);
  return Number.isFinite(t) ? t : null;
}

export function buildSortedRadarFeedEntries(
  markers: Record<string, unknown>[],
  filter: RadarQuickFilter = 'all',
): RadarFeedEntry[] {
  const filtered =
    filter === 'all' ? markers : markers.filter((m) => radarFilterMatchesMarker(filter, m));

  const out: RadarFeedEntry[] = [];
  for (const m of filtered) {
    const sortKey = radarMarkerTimestamp(m);
    const typeKey = String(m.threatType ?? m.threat_type ?? m.type ?? 'unknown');
    const place = String(m.place ?? m.location ?? 'Невідомий регіон');
    const displayTime = String(m.time ?? '--:--');
    out.push({
      raw: m,
      sortKey,
      place,
      typeKey,
      typeLabel: radarThreatTypeLabel(typeKey),
      displayTime,
    });
  }

  out.sort((a, b) => {
    if (a.sortKey == null && b.sortKey == null) return 0;
    if (a.sortKey == null) return 1;
    if (b.sortKey == null) return -1;
    return b.sortKey - a.sortKey;
  });
  return out;
}

export function buildRadarFeedListItems(sorted: RadarFeedEntry[]): RadarListItem[] {
  const now = new Date();
  const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const tomorrow = todayStart + 86400000;

  const today: RadarFeedEntry[] = [];
  const earlier: RadarFeedEntry[] = [];
  for (const e of sorted) {
    const t = e.sortKey;
    if (t != null && t >= todayStart && t < tomorrow) today.push(e);
    else earlier.push(e);
  }

  const out: RadarListItem[] = [];
  if (today.length > 0) {
    out.push({ kind: 'section', title: 'Сьогодні' });
    for (const e of today) out.push({ kind: 'row', entry: e });
  }
  if (earlier.length > 0) {
    out.push({ kind: 'section', title: 'Раніше' });
    for (const e of earlier) out.push({ kind: 'row', entry: e });
  }
  return out;
}
