import { Platform } from 'react-native';

/** Push APIs are iOS/Android only — expo-notifications throws on web. */
export function isPushNotificationsSupported(): boolean {
  return Platform.OS === 'ios' || Platform.OS === 'android';
}
