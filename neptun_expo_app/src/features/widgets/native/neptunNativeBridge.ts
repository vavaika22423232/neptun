import { requireNativeModule } from 'expo-modules-core';
import type { WidgetDataValue } from '../types';

export type { WidgetDataValue };

type NeptunNativeBridgeModule = {
  isAvailable(): boolean;
  setWidgetData(key: string, value: WidgetDataValue): Promise<void>;
  reloadWidget(): Promise<void>;
  startLiveActivity(options: {
    region: string;
    threatType: string;
    threatCount: number;
    isAlarm: boolean;
  }): Promise<void>;
  updateLiveActivity(options: {
    region: string;
    threatType: string;
    threatCount: number;
    isAlarm: boolean;
    startTimeMs?: number;
  }): Promise<void>;
  endLiveActivity(): Promise<void>;
};

let cached: NeptunNativeBridgeModule | null | undefined;

/** Lazy — only resolves inside the React Native / Metro runtime. */
export function getNeptunNativeBridge(): NeptunNativeBridgeModule | null {
  if (cached !== undefined) return cached;
  try {
    cached = requireNativeModule<NeptunNativeBridgeModule>('NeptunNativeBridge');
    return cached;
  } catch {
    cached = null;
    return null;
  }
}
