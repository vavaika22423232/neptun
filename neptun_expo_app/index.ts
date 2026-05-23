import { registerFcmBackgroundHandler } from './src/features/notifications/registerFcmBackground';
import { isFirebaseNativeLinked } from './src/utils/nativeModuleGuard';

if (isFirebaseNativeLinked()) {
  registerFcmBackgroundHandler();
}

import 'expo-router/entry';
