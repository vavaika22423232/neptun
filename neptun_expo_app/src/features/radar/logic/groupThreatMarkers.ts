export type ThreatTypeGroup = {
  type: string;
  markers: Record<string, unknown>[];
};

/** Flutter `radar_tab.dart` `_buildThreatList` grouping. */
export function groupThreatMarkersByType(markers: Record<string, unknown>[]): ThreatTypeGroup[] {
  const map = new Map<string, Record<string, unknown>[]>();
  for (const m of markers) {
    const type = String(m.threatType ?? m.type ?? 'unknown');
    const list = map.get(type) ?? [];
    list.push(m);
    map.set(type, list);
  }
  return [...map.entries()].map(([type, group]) => ({ type, markers: group }));
}

export function placesPreview(markers: Record<string, unknown>[], max = 2): string {
  return markers
    .map((m) => String(m.place ?? m.location ?? '').trim())
    .filter((s) => s.length > 0)
    .slice(0, max)
    .join(', ');
}
