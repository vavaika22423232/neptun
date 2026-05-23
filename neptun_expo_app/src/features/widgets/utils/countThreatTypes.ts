export type ThreatTypeCounts = {
  drones: number;
  missiles: number;
  kab: number;
  ballistic: number;
};

/** Flutter `WidgetService.syncFromRadarSnapshot` threat bucketing. */
export function countThreatTypesFromMarkers(markers: Record<string, unknown>[]): ThreatTypeCounts {
  let drones = 0;
  let missiles = 0;
  let kab = 0;
  let ballistic = 0;

  for (const m of markers) {
    const t = String(m.threatType ?? m.threat_type ?? m.type ?? '').toLowerCase();
    if (t.includes('shahed') || t.includes('drone') || t.includes('fpv')) {
      drones++;
    } else if (t.includes('raketa') || t.includes('missile')) {
      missiles++;
    } else if (t.includes('kab')) {
      kab++;
    } else if (t.includes('ballistic')) {
      ballistic++;
    }
  }

  return { drones, missiles, kab, ballistic };
}
