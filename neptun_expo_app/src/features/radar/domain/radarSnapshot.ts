export type RadarSnapshot = {
  markers: Record<string, unknown>[];
  activeOblastsUnderAlarm: number;
  fetchedAt: number;
  fromDiskCache?: boolean;
};
