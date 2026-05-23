import { useCallback, useEffect, useRef } from 'react';
import {
  createAudioPlayer,
  RecordingPresets,
  requestRecordingPermissionsAsync,
  setAudioModeAsync,
  useAudioRecorder,
  type AudioPlayer,
} from 'expo-audio';

/** Real expo-audio hook — only loaded when `ExpoAudio` is linked (see `useChatVoiceAudio.ts`). */
export function useChatVoiceAudioImpl() {
  const recorder = useAudioRecorder(RecordingPresets.HIGH_QUALITY);
  const playerRef = useRef<AudioPlayer | null>(null);
  const playbackListenerRef = useRef<{ remove: () => void } | null>(null);

  useEffect(() => {
    return () => {
      playbackListenerRef.current?.remove();
      playerRef.current?.release();
      playerRef.current = null;
    };
  }, []);

  const startRecording = useCallback(async () => {
    const { granted } = await requestRecordingPermissionsAsync();
    if (!granted) throw new Error('Немає дозволу на мікрофон');
    await setAudioModeAsync({ allowsRecording: true, playsInSilentMode: true });
    await recorder.prepareToRecordAsync();
    recorder.record();
  }, [recorder]);

  const stopRecording = useCallback(async (): Promise<string | null> => {
    if (recorder.isRecording) {
      await recorder.stop();
    }
    await setAudioModeAsync({ allowsRecording: false, playsInSilentMode: true });
    return recorder.uri;
  }, [recorder]);

  const cancelRecording = useCallback(async () => {
    try {
      if (recorder.isRecording) await recorder.stop();
    } catch {
      /* not started */
    }
    await setAudioModeAsync({ allowsRecording: false, playsInSilentMode: true }).catch(() => undefined);
  }, [recorder]);

  const playUrl = useCallback(async (url: string, onEnd: () => void) => {
    playbackListenerRef.current?.remove();
    playerRef.current?.release();
    const player = createAudioPlayer(url);
    playerRef.current = player;
    playbackListenerRef.current = player.addListener('playbackStatusUpdate', (status) => {
      if (status.didJustFinish) {
        playbackListenerRef.current?.remove();
        player.release();
        if (playerRef.current === player) playerRef.current = null;
        onEnd();
      }
    });
    player.play();
  }, []);

  const stopPlayback = useCallback(() => {
    playbackListenerRef.current?.remove();
    playerRef.current?.pause();
    playerRef.current?.release();
    playerRef.current = null;
  }, []);

  return {
    startRecording,
    stopRecording,
    cancelRecording,
    playUrl,
    stopPlayback,
    isNativeAvailable: true,
  };
}
