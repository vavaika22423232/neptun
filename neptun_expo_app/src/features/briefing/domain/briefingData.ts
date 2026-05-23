export type BriefingData = {
  isMorning: boolean;
  totalAlarmsToday: number;
  alarmRegions: string[];
  drones: number;
  missiles: number;
  kab: number;
  ballistic: number;
  userRegionName: string | null;
  userRegionAlarmCount: number;
  userRegionsTotal: number;
  fromCache: boolean;
};

export function briefingTotalThreats(data: BriefingData): number {
  return data.drones + data.missiles + data.kab + data.ballistic;
}

export function briefingHasMultipleRegions(data: BriefingData): boolean {
  return data.userRegionsTotal > 1;
}
