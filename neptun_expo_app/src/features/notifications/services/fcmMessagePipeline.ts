import { PrefsKeys } from '../../../config/prefsKeys';
import { OBLAST_NAME_TO_ID } from '../constants/oblastIds';
import { persistentStorage } from '../../../services/persistentStorage';
import { shouldBlockSleepNotification } from '../../../services/sleepModeStore';
import { notificationDedup } from '../notificationDedup';
import { isThreatTypeAllowed, resolveThreatKey } from '../logic/resolveThreatKey';
import { shouldAllowByQuietHours } from '../logic/quietHours';
import {
  shouldShowNotification,
  type NotificationEvent,
  type UserRegionSelection,
} from './notificationFilterService';

export type FcmData = Record<string, string | undefined>;

export type FcmDisplayPayload = {
  title: string;
  body: string;
  channelId: 'feedback_alerts' | 'alarm_channel' | 'critical_alerts' | 'normal_alerts';
  data: Record<string, string>;
};

const PLACE_TO_RAION: Record<string, string> = { Слобожанське: 'Чугуївський район' };

function str(v: unknown): string {
  return v == null ? '' : String(v);
}

function loadUserRegionSelection(): UserRegionSelection {
  const oblastIds = new Set(persistentStorage.getStringList('selected_oblast_ids'));
  const legacy = persistentStorage.getString('selected_oblast_id');
  if (legacy) oblastIds.add(legacy);

  const raionIds = new Set(persistentStorage.getStringList('selected_raion_ids'));
  const settlementId = persistentStorage.getString('selected_settlement_id') ?? null;

  if (oblastIds.size === 0 && raionIds.size === 0 && !settlementId) {
    const selectedRegions = persistentStorage.getStringList(PrefsKeys.selectedRegions);
    for (const name of selectedRegions) {
      const id = OBLAST_NAME_TO_ID[name];
      if (id) oblastIds.add(id);
      else raionIds.add(name);
    }
  }

  return { oblastIds, raionIds, settlementId };
}

function passesLegacyRegionFilter(region: string, location: string): boolean {
  const selectedRegions = persistentStorage.getStringList(PrefsKeys.selectedRegions);
  const selectedRaionIds = persistentStorage.getStringList('selected_raion_ids');
  if (selectedRegions.length === 0 && selectedRaionIds.length === 0) return true;

  const placeRaion =
    PLACE_TO_RAION[location.trim()] ?? PLACE_TO_RAION[region.trim()];
  if (placeRaion) {
    const hasRaion =
      selectedRegions.includes(placeRaion) ||
      (selectedRaionIds.includes('UA-63-04') && placeRaion === 'Чугуївський район');
    if (!hasRaion) return false;
  }

  const normalizedRegion = region.toLowerCase().trim();
  const normalizedLocation = location.toLowerCase().trim();
  for (const selected of selectedRegions) {
    const normalizedSelected = selected.toLowerCase().trim();
    if (
      normalizedRegion.includes(normalizedSelected) ||
      normalizedSelected.includes(normalizedRegion) ||
      normalizedLocation.includes(normalizedSelected)
    ) {
      return true;
    }
  }
  return false;
}

function passesRegionFilter(data: FcmData): boolean {
  const oblastId = data.oblast_id?.trim();
  const raionId = data.raion_id?.trim();
  const settlementId = data.settlement_id?.trim();
  const region = str(data.region);
  const location = str(data.location ?? data.city);

  if (oblastId) {
    const user = loadUserRegionSelection();
    const event: NotificationEvent = {
      oblastId,
      raionId: raionId || undefined,
      settlementId: settlementId || undefined,
    };
    return shouldShowNotification(event, user);
  }

  return passesLegacyRegionFilter(region, location);
}

function buildDisplayPayload(data: FcmData, notifTitle?: string, notifBody?: string): FcmDisplayPayload {
  const rawTitle = str(data.title) || notifTitle || 'Тривога';
  const rawBody = str(data.body) || notifBody || '';
  const region = str(data.region);
  const threatType = str(data.threat_type);
  const alarmState = str(data.alarm_state);
  const combined = `${rawTitle} ${rawBody} ${threatType}`.toLowerCase();

  let emoji = '🚨';
  let channelId: FcmDisplayPayload['channelId'] = 'normal_alerts';

  if (combined.includes('відбій') || alarmState === 'end' || alarmState === 'ended') {
    emoji = '✅';
    channelId = 'normal_alerts';
  } else if (
    combined.includes('ракет') ||
    combined.includes('балістик') ||
    combined.includes('каб') ||
    data.is_critical === 'true'
  ) {
    emoji = combined.includes('каб') ? '💣' : '🚀';
    channelId = 'critical_alerts';
  } else if (combined.includes('бпла') || combined.includes('дрон') || combined.includes('шахед')) {
    emoji = '🛩️';
    channelId = 'normal_alerts';
  }

  const title = rawTitle.startsWith(emoji) ? rawTitle : `${emoji} ${rawTitle}`;
  const body =
    rawBody ||
    (region ? `${region}${locationSuffix(data)}` : '') ||
    'Оновлення тривоги';

  const outData: Record<string, string> = {};
  for (const [k, v] of Object.entries(data)) {
    if (v != null && v !== '') outData[k] = v;
  }

  return { title, body, channelId, data: outData };
}

function locationSuffix(data: FcmData): string {
  const loc = str(data.location ?? data.city);
  return loc ? ` — ${loc}` : '';
}

export type PipelineResult =
  | { show: true; payload: FcmDisplayPayload; isFeedback: boolean }
  | { show: false; reason: string };

function isFeedbackType(fcmType: string): boolean {
  return fcmType === 'feedback_reply' || fcmType === 'feedback_status';
}

/**
 * Flutter foreground / background FCM gating (without metrics/TTS/widget side effects).
 */
export function evaluateFcmMessage(
  data: FcmData,
  options: { foreground: boolean; notificationTitle?: string; notificationBody?: string },
): PipelineResult {
  if (!persistentStorage.getBoolean(PrefsKeys.notificationsEnabled, true)) {
    return { show: false, reason: 'notifications_disabled' };
  }

  const fcmType = str(data.type) || 'threat';
  const isAlarmFcm = fcmType === 'alarm';
  const region = str(data.region);
  const location = str(data.location ?? data.city);
  const threatType = str(data.threat_type);
  const alarmState = str(data.alarm_state);
  const rawBody = str(data.body) || options.notificationBody || '';

  if (isFeedbackType(fcmType)) {
    const payload = buildDisplayPayload(
      {
        ...data,
        title: data.title ?? options.notificationTitle ?? "Зворотний зв'язок",
        body: data.body ?? options.notificationBody ?? '',
      },
      options.notificationTitle,
      options.notificationBody,
    );
    return { show: true, payload: { ...payload, channelId: 'feedback_alerts' }, isFeedback: true };
  }

  if (!options.foreground) {
    if (!passesRegionFilter(data)) {
      return { show: false, reason: 'region_filter' };
    }
    if (shouldBlockSleepNotification(rawBody)) {
      return { show: false, reason: 'sleep_mode' };
    }
  }

  if (!isAlarmFcm) {
    const threatKey = resolveThreatKey(rawBody, threatType);
    const allowed = persistentStorage.getStringList('notify_threat_types');
    if (!isThreatTypeAllowed(threatKey, allowed)) {
      return { show: false, reason: 'threat_type_filter' };
    }
  }

  const threatKey = resolveThreatKey(rawBody, threatType);
  const isCritical =
    data.is_critical === 'true' ||
    isAlarmFcm ||
    threatKey === 'rocket' ||
    threatKey === 'ballistic' ||
    threatKey === 'kab';

  if (!shouldAllowByQuietHours(isCritical)) {
    return { show: false, reason: 'quiet_hours' };
  }

  const dedupKey = `notif|${region}|${location}|${threatType}|${alarmState}`;
  if (options.foreground && notificationDedup.isDuplicateInMemory(dedupKey)) {
    return { show: false, reason: 'dedup_memory' };
  }
  if (notificationDedup.shouldSkipNotification(dedupKey)) {
    return { show: false, reason: 'dedup_storage' };
  }
  if (options.foreground) {
    notificationDedup.markShownInMemory(dedupKey);
  }

  if (options.foreground && !passesRegionFilter(data)) {
    return { show: false, reason: 'region_filter' };
  }

  const payload = buildDisplayPayload(data, options.notificationTitle, options.notificationBody);
  if (isAlarmFcm) {
    payload.channelId = 'alarm_channel';
  }

  return { show: true, payload, isFeedback: false };
}
