import { endpoints } from '../../config/api';
import { PrefsKeys } from '../../config/prefsKeys';
import { apiRequest } from '../../services/apiClient';
import { persistentStorage } from '../../services/persistentStorage';

/** Flutter `NotificationPrefsController` */
export const notificationPrefsController = {
  buildPayload(): Record<string, unknown> {
    const threatTypes = persistentStorage.getStringList('notify_threat_types');

    return {
      notifications_enabled: persistentStorage.getBoolean(PrefsKeys.notificationsEnabled, true),
      quiet_hours_enabled: persistentStorage.getBoolean('quiet_hours_enabled', false),
      quiet_hours_start: persistentStorage.getString('quiet_hours_start') ?? '22:00',
      quiet_hours_end: persistentStorage.getString('quiet_hours_end') ?? '07:00',
      quiet_hours_allow_critical: persistentStorage.getBoolean('quiet_hours_allow_critical', true),
      notify_threat_types: threatTypes,
      regions: persistentStorage.getStringList(PrefsKeys.selectedRegions),
      oblast_ids: persistentStorage.getStringList('selected_oblast_ids'),
      raion_ids: persistentStorage.getStringList('selected_raion_ids'),
    };
  },

  async syncToBackend(deviceId: string, fcmToken?: string | null): Promise<void> {
    const body = this.buildPayload();
    body.device_id = deviceId;
    if (fcmToken) body.token = fcmToken;

    try {
      await apiRequest(endpoints.devicePreferences, {
        method: 'PATCH',
        body: JSON.stringify(body),
      });
    } catch (e) {
      const msg = e instanceof Error ? e.message : '';
      if (msg.includes('404') || msg.includes('405')) return;
      throw e;
    }
  },
};
