import Slider from '@react-native-community/slider';
import { Ionicons } from '@expo/vector-icons';
import { useRouter } from 'expo-router';
import * as Linking from 'expo-linking';
import * as Notifications from 'expo-notifications';
import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  Platform,
  Pressable,
  StyleSheet,
  View,
} from 'react-native';
import { ProfileSwitch } from './ProfileSwitch';
import { NeptunBottomSheet } from '../../../components/NeptunBottomSheet';
import { ProfileNavTile } from '../../../components/profile/ProfileNavTile';
import { Text } from '../../../components/Text';
import { ProfileGlassCard } from './ProfileGlassCard';
import { ProfileSectionLabel } from './ProfileSectionLabel';
import { ProFeature, ProGate } from '../../../core/pro/proGate';
import { useApp } from '../../../context/AppContext';
import { ALARM_SOUND_IDS, ALARM_SOUND_LABELS, type AlarmSoundId } from '../constants/alarmSounds';
import {
  patchProfileSettings,
  useProfileSettings,
  VIBRATION_PATTERN_LABELS,
} from '../hooks/useProfileSettings';
import {
  needsBatteryOptimizationWarning,
  requestDisableBatteryOptimization,
} from '../../../services/batteryOptimizationService';
import { isPushNotificationsSupported, notificationService } from '../../../services/notificationService';
import { ttsService } from '../../../services/ttsService';
import { spacing } from '../../../theme/tokens';
import { useLegacyPalette, useProfileTheme, useThemedStyles } from '../../../theme/useAppTheme';
import { fonts } from '../../../theme/fonts';

function SettingsShimmer({ styles, muted }: { styles: ReturnType<typeof useSettingsStyles>; muted: string }) {
  return (
    <ProfileGlassCard style={styles.shimmerCard}>
      <ActivityIndicator color={muted} />
    </ProfileGlassCard>
  );
}

export function SettingsSection() {
  const router = useRouter();
  const { isPremium } = useApp();
  const settings = useProfileSettings();
  const palette = useLegacyPalette();
  const profile = useProfileTheme();
  const styles = useSettingsStyles();
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
      <View>
        <SettingsShimmer styles={styles} muted={palette.textMuted} />
        <SettingsShimmer styles={styles} muted={palette.textMuted} />
        <SettingsShimmer styles={styles} muted={palette.textMuted} />
      </View>
    );
  }

  const topicsPreview =
    settings.subscribedTopics.length === 0
      ? 'Немає підписок'
      : settings.subscribedTopics.slice(0, 5).join(', ') +
        (settings.subscribedTopics.length > 5 ? '…' : '');

  return (
    <View>
      <ProfileNavTile
        icon="notifications"
        label="Сповіщення"
        subtitle={settings.notificationsEnabled ? 'Увімкнено' : 'Вимкнено'}
        iconAccent={palette.accent}
        showDividerBelow
        trailing={
          <ProfileSwitch
            value={settings.notificationsEnabled}
            onValueChange={(value: boolean) => {
              patchProfileSettings({ notificationsEnabled: value });
              void notificationService.setNotificationsEnabled(value).then(() => settings.reload());
            }}
          />
        }
      />
      {pushPermission === 'denied' ? (
        <ProfileNavTile
          icon="alert-circle-outline"
          label="Дозвіл на сповіщення вимкнено"
          subtitle="Відкрийте системні налаштування застосунку"
          iconAccent={palette.warning}
          showDividerBelow
          onPress={() => void Linking.openSettings()}
        />
      ) : null}
      {settings.notificationsEnabled && !settings.pushToken && pushPermission === 'granted' ? (
        <ProfileNavTile
          icon="cloud-offline-outline"
          label="Токен push не отримано"
          subtitle="Перезапустіть застосунок або перевірте збірку (dev client)"
          iconAccent={palette.warning}
          showDividerBelow
        />
      ) : null}
      {settings.pushToken ? (
        <ProfileNavTile
          icon="cloud-done"
          label="Підключено до сервера"
          subtitle="Push-сповіщення активні"
          iconAccent={palette.success}
          showDividerBelow={Platform.OS === 'ios' || settings.regionSelectionCount > 0}
        />
      ) : null}
      {Platform.OS === 'ios' ? (
        <ProfileNavTile
          icon="phone-portrait"
          label="APNs статус"
          subtitle={settings.pushToken ? 'Токен отримано' : 'Токен не отримано'}
          iconAccent={palette.accent}
          showDividerBelow={settings.regionSelectionCount > 0}
        />
      ) : null}
      {settings.regionSelectionCount > 0 ? (
        <ProfileNavTile
          icon="albums"
          label="Підписки на регіони"
          subtitle={`Активно: ${settings.regionSelectionCount}`}
          iconAccent={palette.warning}
          showDividerBelow={settings.notificationsEnabled}
        />
      ) : null}

      {settings.notificationsEnabled ? (
        <ProfileGlassCard style={styles.diagCard}>
          <View style={styles.diagHeader}>
            <Ionicons name="information-circle-outline" size={22} color={palette.accent} />
            <View style={{ flex: 1 }}>
              <Text style={styles.diagTitle}>Діагностика підписки</Text>
              <Text muted style={styles.diagSub}>
                Підписано на: {topicsPreview}
              </Text>
            </View>
          </View>
          <Text muted style={styles.diagHint}>
            Якщо сповіщення не приходять: вимкніть оптимізацію батареї для додатку, дозвольте працювати у
            фоні.
          </Text>
        </ProfileGlassCard>
      ) : null}

      <ProfileSectionLabel title="Звук та вібрація" icon="volume-medium-outline" />
      <ProfileGlassCard style={styles.innerCard}>
        <View style={styles.ttsRow}>
          <Ionicons
            name={settings.ttsEnabled ? 'megaphone' : 'megaphone-outline'}
            size={22}
            color={settings.ttsEnabled ? palette.accent : palette.textMuted}
          />
          <View style={{ flex: 1 }}>
            <Text style={styles.innerTitle}>Голосові сповіщення</Text>
            <Text muted style={styles.innerHint}>
              {settings.ttsEnabled
                ? ttsNativeAvailable
                  ? 'Озвучувати тривоги. Увімкніть український голос у налаштуваннях системи.'
                  : 'Потрібен перезбір dev client (npx expo run:ios) після оновлення залежностей.'
                : 'Вимкнено'}
            </Text>
          </View>
          <ProfileSwitch
            value={settings.ttsEnabled}
            onValueChange={(value) => {
              patchProfileSettings({ ttsEnabled: value });
              void ttsService.setEnabled(value);
              settings.reload();
              void syncPrefs();
            }}
          />
        </View>
        {settings.ttsEnabled ? (
          <>
            <View style={styles.volumeRow}>
              <Ionicons name="volume-low" size={18} color={palette.textMuted} />
              <Slider
                style={styles.volumeSlider}
                minimumValue={0}
                maximumValue={1}
                value={settings.ttsVolume}
                minimumTrackTintColor={palette.accent}
                maximumTrackTintColor={palette.border}
                thumbTintColor={palette.accent}
                onValueChange={(value: number) => {
                  patchProfileSettings({ ttsVolume: value });
                  void ttsService.setVolume(value);
                }}
              />
              <Text style={styles.volumePct}>{Math.round(settings.ttsVolume * 100)}%</Text>
            </View>
            <Pressable
              style={styles.ttsTestBtn}
              onPress={() => {
                void ttsService
                  .initialize()
                  .then(() => ttsService.speakTest())
                  .catch((e: unknown) => {
                    const msg = e instanceof Error ? e.message : 'Помилка TTS';
                    Alert.alert('Голосові сповіщення', msg);
                  });
              }}
            >
              <Ionicons name="play" size={18} color={palette.text} />
              <Text style={styles.ttsTestLabel}>Перевірити голос</Text>
            </Pressable>
          </>
        ) : null}
      </ProfileGlassCard>

      <ProfileNavTile
        icon="notifications"
        label="Звук тривоги"
        subtitle={ALARM_SOUND_LABELS[settings.alarmSoundId as AlarmSoundId] ?? 'За замовчуванням'}
        iconAccent={palette.success}
        showDividerBelow
        onPress={() => setAlarmSheet(true)}
      />
      <ProfileNavTile
        icon="phone-portrait"
        label="Вібрація"
        subtitle={
          settings.vibrationEnabled
            ? VIBRATION_PATTERN_LABELS[settings.vibrationPattern] ?? settings.vibrationPattern
            : 'Вимкнено'
        }
        iconAccent={palette.premium}
        trailing={
          <ProfileSwitch
            value={settings.vibrationEnabled}
            onValueChange={(value) => {
              patchProfileSettings({ vibrationEnabled: value });
              settings.reload();
            }}
          />
        }
        onPress={() => setVibSheet(true)}
      />

      <ProfileSectionLabel title="Режим сну" icon="moon-outline" />
      {ProGate.isUnlockedSync(ProFeature.SleepMode, isPremium) ? (
        <ProfileGlassCard style={styles.innerCard}>
          <View style={styles.ttsRow}>
            <Ionicons name="moon" size={22} color={palette.premium} />
            <View style={{ flex: 1 }}>
              <Text style={styles.innerTitle}>Режим сну</Text>
              <Text muted style={styles.innerHint}>
                {settings.sleepModeEnabled ? 'Увімкнено' : 'Вимкнено'} — налаштування в окремому екрані
              </Text>
            </View>
            <Pressable onPress={() => router.push('/sleep-mode')}>
              <Ionicons name="chevron-forward" size={20} color={palette.textMuted} />
            </Pressable>
          </View>
        </ProfileGlassCard>
      ) : (
        <Pressable onPress={() => router.push('/premium')}>
          <ProfileGlassCard style={styles.innerCard}>
            <View style={styles.ttsRow}>
              <Ionicons name="lock-closed" size={22} color={palette.premium} />
              <View style={{ flex: 1 }}>
                <Text style={styles.innerTitle}>Режим сну — PRO</Text>
                <Text muted style={styles.innerHint}>
                  Вночі — тиша. Але балістика та ракети все одно розбудять.
                </Text>
              </View>
              <Ionicons name="chevron-forward" size={20} color={palette.textMuted} />
            </View>
          </ProfileGlassCard>
        </Pressable>
      )}

      <ProfileSectionLabel title="Діагностика" icon="pulse-outline" />
      {needsBatteryOptimizationWarning() ? (
        <ProfileNavTile
          icon="battery-dead"
          label="Вимкнути оптимізацію батареї"
          subtitle="Для надійних сповіщень на Xiaomi/Huawei"
          iconAccent={palette.warning}
          showDividerBelow
          onPress={() => void requestDisableBatteryOptimization()}
        />
      ) : null}
      <ProfileNavTile
        icon="notifications-outline"
        label="Тестове сповіщення"
        subtitle="Перевірити доставку"
        iconAccent={palette.accent}
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
              <Ionicons
                name={selected ? 'checkmark-circle' : 'ellipse-outline'}
                size={22}
                color={canSelect ? palette.accent : palette.textMuted}
              />
              <Text style={styles.soundLabel}>{ALARM_SOUND_LABELS[id]}</Text>
              {!canSelect ? <Text style={styles.proLock}>PRO</Text> : null}
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
              <Ionicons
                name={selected ? 'checkmark-circle' : 'ellipse-outline'}
                size={22}
                color={palette.accent}
              />
              <Text style={styles.soundLabel}>{VIBRATION_PATTERN_LABELS[id]}</Text>
            </Pressable>
          );
        })}
      </NeptunBottomSheet>
    </View>
  );
}

function useSettingsStyles() {
  return useThemedStyles((t) => {
    const palette = t.palette;
    const profile = t.profile;
    return StyleSheet.create({
      shimmerCard: {
        minHeight: 56,
        alignItems: 'center',
        justifyContent: 'center',
        marginHorizontal: 16,
        marginVertical: spacing.md,
      },
      diagCard: {
        marginHorizontal: 16,
        marginBottom: spacing.md,
        gap: 10,
      },
      diagHeader: {
        flexDirection: 'row',
        gap: 14,
        alignItems: 'flex-start',
      },
      diagTitle: {
        fontFamily: fonts.medium,
        fontSize: 14,
        color: palette.text,
      },
      diagSub: { fontSize: 12, marginTop: 2, color: palette.textMuted },
      diagHint: { fontSize: 11, lineHeight: 16, color: palette.textMuted },
      innerCard: {
        marginHorizontal: 16,
        marginBottom: spacing.md,
      },
      ttsRow: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 14,
      },
      volumeRow: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 8,
        marginTop: 16,
        paddingLeft: 36,
      },
      volumeSlider: {
        flex: 1,
        height: 32,
      },
      volumePct: {
        fontFamily: fonts.semiBold,
        fontSize: 13,
        color: palette.accent,
        width: 40,
        textAlign: 'right',
      },
      ttsTestBtn: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 6,
        marginTop: 12,
        paddingVertical: 10,
        paddingHorizontal: 16,
        borderRadius: 12,
        backgroundColor: palette.accentMuted,
        alignSelf: 'center',
      },
      ttsTestLabel: {
        fontFamily: fonts.semiBold,
        fontSize: 14,
        color: palette.text,
      },
      innerTitle: {
        fontFamily: fonts.medium,
        fontSize: 14,
        color: palette.text,
      },
      innerHint: {
        fontSize: 12,
        marginTop: 2,
        lineHeight: 16,
        color: palette.textMuted,
      },
      sheetTitle: {
        fontFamily: fonts.bold,
        fontSize: 20,
        marginBottom: 16,
        color: palette.text,
      },
      soundOpt: {
        flexDirection: 'row',
        alignItems: 'center',
        gap: 12,
        padding: 14,
        marginBottom: 10,
        backgroundColor: profile.iconBg,
        borderRadius: profile.radiusRow,
      },
      soundOptSelected: {
        backgroundColor: palette.accentMuted,
        borderWidth: StyleSheet.hairlineWidth,
        borderColor: palette.accent + '44',
        borderRadius: profile.radiusRow,
      },
      soundLabel: {
        flex: 1,
        fontFamily: fonts.semiBold,
        fontSize: 15,
        color: palette.text,
      },
      proLock: {
        fontFamily: fonts.bold,
        fontSize: 11,
        color: palette.premium,
      },
    });
  });
}
