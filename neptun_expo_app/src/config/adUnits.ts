import { Platform } from 'react-native';

const PROD_ANDROID_APP = 'ca-app-pub-1995509849440582~8995763934';
const PROD_IOS_APP = 'ca-app-pub-1995509849440582~7835319378';

/** Flutter `AdService` production + Google test IDs in `__DEV__`. */
export const adMobAppIds = {
  android: PROD_ANDROID_APP,
  ios: PROD_IOS_APP,
};

export function bannerAdUnitId(): string {
  if (Platform.OS === 'android') {
    return __DEV__
      ? 'ca-app-pub-3940256099942544/6300978111'
      : 'ca-app-pub-1995509849440582/1226737518';
  }
  if (Platform.OS === 'ios') {
    return __DEV__
      ? 'ca-app-pub-3940256099942544/2934735716'
      : 'ca-app-pub-1995509849440582/5593859915';
  }
  return '';
}

export function appOpenAdUnitId(): string {
  if (Platform.OS === 'android') {
    return __DEV__
      ? 'ca-app-pub-3940256099942544/9257395921'
      : 'ca-app-pub-1995509849440582/5738204880';
  }
  if (Platform.OS === 'ios') {
    return __DEV__
      ? 'ca-app-pub-3940256099942544/5575463023'
      : 'ca-app-pub-1995509849440582/1062877523';
  }
  return '';
}
