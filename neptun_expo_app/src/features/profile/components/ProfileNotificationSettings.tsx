import { useRouter } from 'expo-router';
import * as Linking from 'expo-linking';
import * as Notifications from 'expo-notifications';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { ActivityIndicator, Alert, Pressable, StyleSheet, View } from 'react-native';
import { NeptunBottomSheet } from '../../../components/NeptunBottomSheet';
import { Text } from '../../../components/Text';
import { useApp } from '../../../context/AppContext';
import {
  needsBatteryOptimizationWarning,
  requestDisableBatteryOptimization,
} from '../../../services/batteryOptimizationService';
import { isPushNotificationsSupported, notificationService } from '../../../services/notificationService';
import { ttsService } from '../../../services/ttsService';
import { fonts } from '../../../theme/fonts';
import { useLegacyPalette, useThemedStyles } from '../../../theme/useAppTheme';
import { ALARM_SOUND_IDS, ALARM_SOUND_LABELS, type AlarmSoundId } from '../constants/alarmSounds';
import {
  patchProfileSettings,
  useProfileSettings,
  VIBRATION_PATTERN_LABELS,
} from '../hooks/useProfileSettings';
import { SettingsRow } from './settings/SettingsRow';
import { SettingsToggleRow } from './settings/SettingsToggleRow';

export function ProfileNotificationSettings() {
  const router = useRouter();
  const { isPremium } = useApp();
  const settings = useProfileSettings();
  const palette = useLegacyPalette();
  const styles = useSheetStyles();
  const [alarmSheet, setAlarmSheet] = useState(false);
  const [vibSheet, setVibSheet] = useState(false);
  const [testPending, setTestPending] = useState(false);
  const [pushPermission, setPushPermission] = useState<Notifications.PermissionStatus | null>(null);
  const ttsNativeAvailable = useMemo(() => ttsService.isNativeAvailable(), []);

  useEffect(() => {
    if (!isPushNotificationsSupported()) return;
    void Notifications.getPermissionsAsync().then(({ status }) => setPushPermission(status));
  }, [settings.notificationsEnabled]);

  const syncPrefs = useCallback(async () => {
    try {
      await notificationService.syncPreferencesToBackend();
    } catch {
      /* offline */
    }
  }, []);

  if (settings.loading) {
    return (
      <View style={styles.loading}>
        <ActivityIndicator color={palette.textMuted} />
      </View>
    );
  }

  return (
    <>
      <SettingsToggleRow
        icon="notifications-outline"
        label="Сповіщення"
        subtitle="Увімкнути або вимкнути push-попередження"
        enabled={settings.notificationsEnabled}
        showDivider
        onEnabledChange={(value) => {
          patchProfileSettings({ notificationsEnabled: value });
          void notificationService.setNotificationsEnabled(value).then(() => settings.reload());
        }}
      />

      {pushPermission === 'denied' ? (
        <SettingsRow
          icon="alert-circle-outline"
          label="Дозвіл на сповіщення вимкнено"
          subtitle="Відкрийте системні налаштування застосунку"
          showDivider
          onPress={() => void Linking.openSettings()}
        />
      ) : null}

      <SettingsRow
        icon="volume-high-outline"
        label="Звук тривоги"
        subtitle="Мелодія для push-попереджень"
        detail={ALARM_SOUND_LABELS[settings.alarmSoundId as AlarmSoundId] ?? 'Стандарт'}
        showDivider
        onPress={() => setAlarmSheet(true)}
      />

      <SettingsToggleRow
        icon="phone-portrait-outline"
        label="Вібрація"
        subtitle={
          settings.vibrationEnabled
            ? VIBRATION_PATTERN_LABELS[settings.vibrationPattern] ?? settings.vibrationPattern
            : 'Вимкнено'
        }
        enabled={settings.vibrationEnabled}
        showDivider
        onPress={() => setVibSheet(true)}
        onEnabledChange={(value) => {
          patchProfileSettings({ vibrationEnabled: value });
          settings.reload();
        }}
      />

      <SettingsToggleRow
        icon="megaphone-outline"
        label="Голосові сповіщення"
        subtitle={
          settings.ttsEnabled
            ? 'Озвучування тривог голосом'
            : 'Вимкнено'
        }
        enabled={settings.ttsEnabled}
        showDivider
        onEnabledChange={(value) => {
          if (!ttsNativeAvailable) return;
          patchProfileSettings({ ttsEnabled: value });
          void ttsService.setEnabled(value);
          settings.reload();
          void syncPrefs();
        }}
      />

      {needsBatteryOptimizationWarning() ? (
        <SettingsRow
          icon="battery-charging-outline"
          label="Оптимізація батареї"
          subtitle="Потрібно для надійних сповіщень на деяких пристроях"
          showDivider
          onPress={() => void requestDisableBatteryOptimization()}
        />
      ) : null}

      <SettingsRow
        icon="paper-plane-outline"
        label="Тестове сповіщення"
        subtitle="Перевірити, чи доходять push-повідомлення"
        onPress={() => {
          if (testPending) return;
          setTestPending(true);
          void notificationService
            .sendTestNotification()
            .then(() => Alert.alert('NEPTUN', 'Тестове сповіщення надіслано'))
            .catch((e) => Alert.alert('Помилка', e instanceof Error ? e.message : String(e)))
            .finally(() => setTestPending(false));
        }}
      />

      <NeptunBottomSheet visible={alarmSheet} onClose={() => setAlarmSheet(false)} maxHeightRatio={0.42}>
        <Text style={styles.sheetTitle}>Звук тривоги</Text>
        {ALARM_SOUND_IDS.map((id) => {
          const canSelect = id === 'default' || isPremium;
          const selected = settings.alarmSoundId === id;
          return (
            <Pressable
              key={id}
              style={[styles.soundOpt, selected && styles.soundOptSelected]}
              onPress={() => {
                if (!canSelect) {
                  setAlarmSheet(false);
                  router.push('/premium');
                  return;
                }
                patchProfileSettings({ alarmSoundId: id });
                settings.reload();
                void syncPrefs();
                setAlarmSheet(false);
              }}
            >
              <Text style={[styles.soundLabel, selected && styles.soundLabelSelected]}>{ALARM_SOUND_LABELS[id]}</Text>
              {!canSelect ? <Text style={styles.proLock}>PRO</Text> : null}
              {selected ? <Text style={styles.check}>✓</Text> : null}
            </Pressable>
          );
        })}
      </NeptunBottomSheet>

      <NeptunBottomSheet visible={vibSheet} onClose={() => setVibSheet(false)} maxHeightRatio={0.45}>
        <Text style={styles.sheetTitle}>Патерн вібрації</Text>
        {Object.keys(VIBRATION_PATTERN_LABELS).map((id) => {
          const selected = settings.vibrationPattern === id;
          return (
            <Pressable
              key={id}
              style={[styles.soundOpt, selected && styles.soundOptSelected]}
              onPress={() => {
                patchProfileSettings({ vibrationPattern: id, vibrationEnabled: true });
                settings.reload();
                setVibSheet(false);
              }}
            >
              <Text style={[styles.soundLabel, selected && styles.soundLabelSelected]}>
                {VIBRATION_PATTERN_LABELS[id]}
              </Text>
              {selected ? <Text style={styles.check}>✓</Text> : null}
            </Pressable>
          );
        })}
      </NeptunBottomSheet>
    </>
  );
}

function useSheetStyles() {
  return useThemedStyles((t) =>
    StyleSheet.create({
      loading: {
        minHeight: 88,
        alignItems: 'center',
        justifyContent: 'center',
      },
      sheetTitle: {
        fontFamily: fonts.semiBold,
        fontSize: 17,
        marginBottom: 12,
        color: t.colors.textPrimary,
      },
      soundOpt: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 12,
        paddingVertical: 13,
        paddingHorizontal: 14,
        marginBottom: 6,
        borderRadius: t.radii.md,
        backgroundColor: t.colors.surfaceSoft,
      },
      soundOptSelected: {
        backgroundColor: t.colors.primaryMuted,
      },
      soundLabel: {
        flex: 1,
        fontFamily: fonts.regular,
        fontSize: 16,
        color: t.colors.textPrimary,
      },
      soundLabelSelected: {
        fontFamily: fonts.medium,
      },
      proLock: {
        fontFamily: fonts.bold,
        fontSize: 11,
        color: t.colors.pro,
      },
      check: {
        fontFamily: fonts.semiBold,
        fontSize: 16,
        color: t.colors.primary,
      },
    }),
  );
}
