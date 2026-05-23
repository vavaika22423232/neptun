import { Platform } from 'react-native';
import { PrefsKeys } from '../../../config/prefsKeys';
import { isPremiumFromPrefs } from '../../premium/isPremiumFromPrefs';
import { persistentStorage } from '../../../services/persistentStorage';
import type { WidgetDataValue } from '../types';
import { isHomeWidgetBridgeAvailable, reloadHomeWidget, setWidgetData } from '../native/homeWidgetBridge';
import { countThreatTypesFromMarkers } from '../utils/countThreatTypes';

const WIDGET_USER_REGION_KEY = 'widget_user_region';

export type WidgetUpdateParams = {
  region: string;
  isAlarm: boolean;
  threatsCount: number;
  timerMinutes: number;
  totalAlarms?: number;
  threatType?: string;
  dronesCount?: number;
  missilesCount?: number;
  kabCount?: number;
  ballisticCount?: number;
  totalThreats?: number;
};

function isNativePlatform(): boolean {
  return Platform.OS === 'ios' || Platform.OS === 'android';
}

async function persistAndReload(entries: Record<string, WidgetDataValue>): Promise<void> {
  if (!isHomeWidgetBridgeAvailable()) return;
  for (const [key, value] of Object.entries(entries)) {
    await setWidgetData(key, value);
  }
  await reloadHomeWidget();
}

async function showPremiumRequired(): Promise<void> {
  await persistAndReload({
    widget_region: 'Premium',
    widget_is_alarm: false,
    widget_status_text: 'Придбайте Premium',
    widget_total_alarms: 0,
    widget_last_update: Date.now(),
  });
}

export const widgetService = {
  async initialize(): Promise<void> {
    if (!isNativePlatform()) return;
    /* App group / prefs are configured at prebuild; no-op when bridge missing. */
  },

  async applyNonPremiumWidgetState(): Promise<void> {
    if (!isNativePlatform()) return;
    await showPremiumRequired();
  },

  async updateWidget(params: WidgetUpdateParams): Promise<void> {
    if (!isNativePlatform()) return;
    if (!isPremiumFromPrefs()) {
      await showPremiumRequired();
      return;
    }

    await persistAndReload({
      widget_status_text: null,
      widget_region: params.region,
      widget_is_alarm: params.isAlarm,
      widget_threats_count: params.threatsCount,
      widget_timer_minutes: params.timerMinutes,
      widget_total_alarms: params.totalAlarms ?? 0,
      widget_threat_type: params.threatType ?? '',
      widget_drones_count: params.dronesCount ?? 0,
      widget_missiles_count: params.missilesCount ?? 0,
      widget_kab_count: params.kabCount ?? 0,
      widget_ballistic_count: params.ballisticCount ?? 0,
      widget_total_threats: params.totalThreats ?? params.threatsCount,
      widget_last_update: Date.now(),
    });
  },

  async syncFromRadarSnapshot(
    markers: Record<string, unknown>[],
    activeOblastsUnderAlarm: number,
  ): Promise<void> {
    if (!isNativePlatform()) return;
    if (!isPremiumFromPrefs()) {
      await showPremiumRequired();
      return;
    }

    const counts = countThreatTypesFromMarkers(markers);
    const region = (await widgetService.getUserRegion()) ?? 'Україна';

    await widgetService.updateWidget({
      region,
      isAlarm: activeOblastsUnderAlarm > 0,
      threatsCount: markers.length,
      timerMinutes: 0,
      totalAlarms: activeOblastsUnderAlarm,
      dronesCount: counts.drones,
      missilesCount: counts.missiles,
      kabCount: counts.kab,
      ballisticCount: counts.ballistic,
      totalThreats: markers.length,
    });
  },

  async updateAlarmStatus(options: {
    isAlarm: boolean;
    region?: string | null;
    totalAlarms?: number;
    threatType?: string;
  }): Promise<void> {
    if (!isNativePlatform()) return;
    if (!isPremiumFromPrefs()) {
      await showPremiumRequired();
      return;
    }

    const entries: Record<string, WidgetDataValue> = {
      widget_is_alarm: options.isAlarm,
      widget_total_alarms: options.totalAlarms ?? 0,
      widget_threat_type: options.threatType ?? '',
      widget_last_update: Date.now(),
    };
    if (options.region) entries.widget_region = options.region;
    await persistAndReload(entries);
  },

  async updateThreatsCount(count: number): Promise<void> {
    if (!isPremiumFromPrefs()) {
      await showPremiumRequired();
      return;
    }
    await persistAndReload({
      widget_threats_count: count,
      widget_last_update: Date.now(),
    });
  },

  async updateTimer(minutes: number): Promise<void> {
    if (!isPremiumFromPrefs()) {
      await showPremiumRequired();
      return;
    }
    await persistAndReload({
      widget_timer_minutes: minutes,
      widget_last_update: Date.now(),
    });
  },

  async setUserRegion(region: string): Promise<void> {
    persistentStorage.setString(WIDGET_USER_REGION_KEY, region);
    if (!isPremiumFromPrefs()) {
      await showPremiumRequired();
      return;
    }
    await persistAndReload({ widget_region: region });
  },

  async getUserRegion(): Promise<string | null> {
    const saved = persistentStorage.getString(WIDGET_USER_REGION_KEY);
    if (saved) return saved;
    const regions = persistentStorage.getStringList(PrefsKeys.selectedRegions);
    return regions[0]?.trim() || null;
  },

  async resetWidget(): Promise<void> {
    if (!isPremiumFromPrefs()) {
      await showPremiumRequired();
      return;
    }
    await widgetService.updateWidget({
      region: 'Оберіть регіон',
      isAlarm: false,
      threatsCount: 0,
      timerMinutes: 0,
      totalAlarms: 0,
      threatType: '',
    });
  },
};
