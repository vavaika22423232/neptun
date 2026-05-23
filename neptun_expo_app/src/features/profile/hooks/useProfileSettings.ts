import { useCallback, useEffect, useMemo, useState } from 'react';
import { PrefsKeys } from '../../../config/prefsKeys';
import { persistentStorage } from '../../../services/persistentStorage';
import { isPushNotificationsSupported } from '../../../services/notificationService';

export type ProfileSettingsState = {
  loading: boolean;
  notificationsEnabled: boolean;
  darkModeEnabled: boolean;
  pushToken: string | null;
  regionSelectionCount: number;
  subscribedTopics: string[];
  ttsEnabled: boolean;
  ttsVolume: number;
  sleepModeEnabled: boolean;
  vibrationEnabled: boolean;
  vibrationPattern: string;
  alarmSoundId: string;
};

const DEFAULT: ProfileSettingsState = {
  loading: true,
  notificationsEnabled: true,
  darkModeEnabled: true,
  pushToken: null,
  regionSelectionCount: 0,
  subscribedTopics: [],
  ttsEnabled: false,
  ttsVolume: 1,
  sleepModeEnabled: false,
  vibrationEnabled: true,
  vibrationPattern: 'auto',
  alarmSoundId: 'default',
};

export function useProfileSettings(): ProfileSettingsState & { reload: () => void } {
  const [state, setState] = useState<ProfileSettingsState>(DEFAULT);

  const reload = useCallback(() => {
    const oblastIds = persistentStorage.getStringList('selected_oblast_ids');
    const raionIds = persistentStorage.getStringList('selected_raion_ids');
    const regions = persistentStorage.getStringList(PrefsKeys.selectedRegions);
    const count =
      oblastIds.length + raionIds.length > 0
        ? oblastIds.length + raionIds.length
        : regions.length;

    setState({
      loading: false,
      notificationsEnabled: persistentStorage.getBoolean(PrefsKeys.notificationsEnabled, true),
      darkModeEnabled: persistentStorage.getBoolean(PrefsKeys.darkMode, true),
      pushToken: isPushNotificationsSupported()
        ? persistentStorage.getString(PrefsKeys.fcmToken) ?? null
        : null,
      regionSelectionCount: count,
      subscribedTopics: persistentStorage.getStringList(PrefsKeys.subscribedTopics),
      ttsEnabled: persistentStorage.getBoolean(PrefsKeys.ttsEnabled, false),
      ttsVolume: Number(persistentStorage.getString(PrefsKeys.ttsVolume) ?? '1') || 1,
      sleepModeEnabled: persistentStorage.getBoolean(PrefsKeys.sleepModeEnabled, false),
      vibrationEnabled: persistentStorage.getBoolean(PrefsKeys.vibrationEnabled, true),
      vibrationPattern: persistentStorage.getString(PrefsKeys.vibrationPattern) ?? 'auto',
      alarmSoundId: persistentStorage.getString(PrefsKeys.alarmSoundId) ?? 'default',
    });
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  return useMemo(() => ({ ...state, reload }), [state, reload]);
}

export function patchProfileSettings(patch: Partial<ProfileSettingsState>): void {
  if (patch.notificationsEnabled != null) {
    persistentStorage.setBoolean(PrefsKeys.notificationsEnabled, patch.notificationsEnabled);
  }
  if (patch.darkModeEnabled != null) {
    persistentStorage.setBoolean(PrefsKeys.darkMode, patch.darkModeEnabled);
  }
  if (patch.ttsEnabled != null) {
    persistentStorage.setBoolean(PrefsKeys.ttsEnabled, patch.ttsEnabled);
  }
  if (patch.ttsVolume != null) {
    persistentStorage.setString(PrefsKeys.ttsVolume, String(patch.ttsVolume));
  }
  if (patch.sleepModeEnabled != null) {
    persistentStorage.setBoolean(PrefsKeys.sleepModeEnabled, patch.sleepModeEnabled);
  }
  if (patch.vibrationEnabled != null) {
    persistentStorage.setBoolean(PrefsKeys.vibrationEnabled, patch.vibrationEnabled);
  }
  if (patch.vibrationPattern != null) {
    persistentStorage.setString(PrefsKeys.vibrationPattern, patch.vibrationPattern);
  }
  if (patch.alarmSoundId != null) {
    persistentStorage.setString(PrefsKeys.alarmSoundId, patch.alarmSoundId);
  }
}

export const VIBRATION_PATTERN_LABELS: Record<string, string> = {
  auto: 'Авто',
  short: 'Коротка',
  long: 'Довга',
  pulse: 'Імпульс',
};
