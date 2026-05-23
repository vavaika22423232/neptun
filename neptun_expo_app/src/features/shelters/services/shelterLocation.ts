import { hasNativeModule } from '../../../utils/nativeModuleGuard';

type LocationModule = typeof import('expo-location');

let cache: LocationModule | null | undefined;
let failed = false;

export function isShelterLocationAvailable(): boolean {
  return hasNativeModule('ExpoLocation');
}

function getLocationModule(): LocationModule | null {
  if (failed) return null;
  if (cache !== undefined) return cache;
  if (!isShelterLocationAvailable()) {
    failed = true;
    cache = null;
    return null;
  }
  try {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    cache = require('expo-location') as LocationModule;
  } catch {
    failed = true;
    cache = null;
  }
  return cache;
}

export async function requestShelterForegroundPermission(): Promise<{
  granted: boolean;
  unavailable: boolean;
}> {
  const Location = getLocationModule();
  if (!Location) {
    return { granted: false, unavailable: true };
  }
  const perm = await Location.requestForegroundPermissionsAsync();
  return { granted: perm.granted, unavailable: false };
}

export async function getShelterCurrentPosition(): Promise<{
  lat: number;
  lon: number;
  unavailable: boolean;
}> {
  const Location = getLocationModule();
  if (!Location) {
    return { lat: 0, lon: 0, unavailable: true };
  }
  const enabled = await Location.hasServicesEnabledAsync();
  if (!enabled) {
    throw new Error('Увімкніть геолокацію для пошуку укриттів');
  }
  const pos = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.High });
  return { lat: pos.coords.latitude, lon: pos.coords.longitude, unavailable: false };
}
