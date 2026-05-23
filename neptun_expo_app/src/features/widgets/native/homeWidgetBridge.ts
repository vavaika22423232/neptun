import { Platform } from 'react-native';
import type { WidgetDataValue } from '../types';
import { getNeptunNativeBridge } from './neptunNativeBridge';

export type { WidgetDataValue };

export function isHomeWidgetBridgeAvailable(): boolean {
  if (Platform.OS !== 'ios' && Platform.OS !== 'android') return false;
  return getNeptunNativeBridge()?.isAvailable() ?? false;
}

export async function setWidgetData(key: string, value: WidgetDataValue): Promise<void> {
  const bridge = getNeptunNativeBridge();
  if (!bridge) return;
  await bridge.setWidgetData(key, value);
}

export async function reloadHomeWidget(): Promise<void> {
  const bridge = getNeptunNativeBridge();
  if (!bridge) return;
  await bridge.reloadWidget();
}
