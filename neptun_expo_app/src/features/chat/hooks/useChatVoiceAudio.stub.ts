const REBUILD_MSG =
  'Голосовий чат потребує перезбірки: npx expo prebuild --clean && npx expo run:ios --device';

export function useChatVoiceAudioStub() {
  const unavailable = async () => {
    throw new Error(REBUILD_MSG);
  };

  return {
    startRecording: unavailable,
    stopRecording: async () => null as string | null,
    cancelRecording: async () => undefined,
    playUrl: async (_url: string, onEnd: () => void) => {
      onEnd();
    },
    stopPlayback: () => undefined,
    isNativeAvailable: false,
  };
}
