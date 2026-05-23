import { hasNativeModule } from '../../../utils/nativeModuleGuard';
import { useChatVoiceAudioStub } from './useChatVoiceAudio.stub';

/** Stable for the app session — safe to branch hooks (native linked or not). */
const EXPO_AUDIO_LINKED = hasNativeModule('ExpoAudio');

/**
 * Flutter `chat_controller` voice record/playback — expo-audio (SDK 54).
 * Loads native implementation only when `ExpoAudio` is linked in the dev client.
 */
export function useChatVoiceAudio() {
  if (EXPO_AUDIO_LINKED) {
    // Must NOT use `.native.ts` filename — Metro auto-picks it on iOS and loads expo-audio at import time.
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const { useChatVoiceAudioImpl } = require('./useChatVoiceAudio.impl') as typeof import('./useChatVoiceAudio.impl');
    return useChatVoiceAudioImpl();
  }
  return useChatVoiceAudioStub();
}
