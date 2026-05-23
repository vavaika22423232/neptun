import { Platform } from 'react-native';
import { getNeptunNativeBridge } from '../native/neptunNativeBridge';

export type LiveActivityThreatType = 'air' | 'ballistic' | 'drones';

function resolveLiveThreatType(threatType: string): LiveActivityThreatType {
  const lower = threatType.toLowerCase();
  if (
    lower.includes('баліст') ||
    lower.includes('ballistic') ||
    lower.includes('ракет')
  ) {
    return 'ballistic';
  }
  if (
    lower.includes('бпла') ||
    lower.includes('drone') ||
    lower.includes('shahed')
  ) {
    return 'drones';
  }
  return 'air';
}

/** Flutter `LiveActivityService` — Dynamic Island + lock screen (iOS 16.2+). */
export const liveActivityService = {
  async start(options: {
    region: string;
    threatType?: string;
    threatCount?: number;
    isAlarm?: boolean;
  }): Promise<void> {
    if (Platform.OS !== 'ios') return;
    const bridge = getNeptunNativeBridge();
    if (!bridge) return;
    await bridge.startLiveActivity({
      region: options.region,
      threatType: resolveLiveThreatType(options.threatType ?? ''),
      threatCount: options.threatCount ?? 1,
      isAlarm: options.isAlarm ?? true,
    });
  },

  async update(options: {
    region: string;
    threatType?: string;
    threatCount?: number;
    isAlarm?: boolean;
    startTime?: Date;
  }): Promise<void> {
    if (Platform.OS !== 'ios') return;
    const bridge = getNeptunNativeBridge();
    if (!bridge) return;
    await bridge.updateLiveActivity({
      region: options.region,
      threatType: resolveLiveThreatType(options.threatType ?? ''),
      threatCount: options.threatCount ?? 1,
      isAlarm: options.isAlarm ?? true,
      startTimeMs: options.startTime?.getTime(),
    });
  },

  async end(): Promise<void> {
    if (Platform.OS !== 'ios') return;
    const bridge = getNeptunNativeBridge();
    if (!bridge) return;
    await bridge.endLiveActivity();
  },

  /** Flutter notification pipeline threat type mapping. */
  resolveLiveThreatType,
};
