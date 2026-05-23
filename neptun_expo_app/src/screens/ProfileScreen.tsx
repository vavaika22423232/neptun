import * as Linking from 'expo-linking';
import { useRouter } from 'expo-router';
import { useCallback, useState } from 'react';
import { Alert, RefreshControl, ScrollView, StyleSheet, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { bottomNavOccupiedHeight } from '../components/BottomNavigationBar';
import { AppConstants } from '../config/constants';
import { RoutePaths } from '../core/navigation/routePaths';
import { ProFeature, ProGate } from '../core/pro/proGate';
import { openNeptunTelegramChannel } from '../core/utils/openNeptunTelegram';
import { useApp } from '../context/AppContext';
import { AccountStatusCard, buildAccountStatusCopy } from '../features/profile/components/AccountSummaryCard';
import { DeveloperDiagnosticsSection } from '../features/profile/components/DeveloperDiagnosticsSection';
import { ProfileHeroStack } from '../features/profile/components/ProfileHeroStack';
import { ProfileLogoutButton } from '../features/profile/components/ProfileLogoutButton';
import { ProfileNotificationSettings } from '../features/profile/components/ProfileNotificationSettings';
import { ProfileThemeRow } from '../features/profile/components/ProfileThemeRow';
import { ProUpgradeCard } from '../features/profile/components/ProUpgradeCard';
import { SettingsRow } from '../features/profile/components/settings/SettingsRow';
import { SettingsSection } from '../features/profile/components/settings/SettingsSection';
import { useProfileSettings } from '../features/profile/hooks/useProfileSettings';
import { regionSelectionLabel } from '../features/profile/utils/regionSelectionLabel';
import { profileTokens } from '../features/profile/profileTokens';
import { useProAccess } from '../features/pro/hooks/useProAccess';
import { useLegacyPalette, useThemedStyles } from '../theme/useAppTheme';

export function ProfileScreen() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const { nickname, isPremium, isModerator, refreshIdentity } = useApp();
  const settings = useProfileSettings();
  const { openPaywall } = useProAccess();
  const palette = useLegacyPalette();
  const [refreshing, setRefreshing] = useState(false);

  const styles = useThemedStyles((t) =>
    StyleSheet.create({
      root: {
        flex: 1,
        backgroundColor: t.colors.cardMuted,
      },
      scroll: {
        paddingTop: 8,
        paddingBottom: bottomNavOccupiedHeight(insets.bottom) + 16,
        gap: profileTokens.groupGap,
      },
    }),
  );

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    try {
      await refreshIdentity();
      settings.reload();
    } finally {
      setRefreshing(false);
    }
  }, [refreshIdentity, settings.reload]);

  const notificationsActive =
    settings.notificationsEnabled && Boolean(settings.pushToken);
  const sleepUnlocked = ProGate.isUnlockedSync(ProFeature.SleepMode, isPremium);

  const account = buildAccountStatusCopy({
    nickname,
    isPremium,
    notificationsActive,
    regionCount: settings.regionSelectionCount,
  });

  return (
    <View style={styles.root}>
      <ScrollView
        contentContainerStyle={styles.scroll}
        showsVerticalScrollIndicator={false}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={palette.accent} />
        }
      >
        <ProfileHeroStack>
          <AccountStatusCard
            title={account.title}
            subtitle={account.subtitle}
            onPress={() => router.push('/regions')}
          />
          <ProUpgradeCard />
        </ProfileHeroStack>

        <SettingsSection
          title="Регіони"
          subtitle="Області та міста, за якими отримуватимете тривоги"
        >
          <SettingsRow
            icon="location-outline"
            label="Обрані регіони"
            subtitle={regionSelectionLabel(settings.regionSelectionCount)}
            showDivider
            onPress={() => router.push('/regions')}
          />
        </SettingsSection>

        <SettingsSection
          title="PRO та персоналізація"
          subtitle="Розумні фільтри та тихий режим вночі"
        >
          <SettingsRow
            icon="options-outline"
            iconTone="pro"
            label="Розумні сповіщення"
            subtitle="Фільтруйте типи загроз і час сповіщень"
            badge={isPremium ? undefined : 'PRO'}
            showDivider
            onPress={() =>
              isPremium
                ? router.push(RoutePaths.smartNotifications)
                : openPaywall({ source: 'profile', lockedFeature: 'smart_notifications' })
            }
          />
          <SettingsRow
            icon="moon-outline"
            iconTone="pro"
            label="Режим сну"
            subtitle="Тиша вночі, окрім критичних загроз"
            badge={sleepUnlocked ? undefined : 'PRO'}
            onPress={() =>
              sleepUnlocked
                ? router.push('/sleep-mode')
                : openPaywall({ source: 'profile', lockedFeature: 'quiet_mode' })
            }
          />
        </SettingsSection>

        <SettingsSection
          title="Сповіщення"
          subtitle="Push, звук, вібрація та голосові попередження"
        >
          <ProfileNotificationSettings />
        </SettingsSection>

        <SettingsSection
          title="Radar та аналітика"
          subtitle="Брифінги, історія тривог і карти загроз"
        >
          <SettingsRow
            icon="newspaper-outline"
            label="Брифінг дня"
            subtitle="Короткий звод подій за сьогодні"
            showDivider
            onPress={() => router.push(RoutePaths.briefing)}
          />
          <SettingsRow
            icon="time-outline"
            label="Історія тривог"
            subtitle="Архів попередніх тривог по регіонах"
            badge={isPremium ? undefined : '24 год'}
            showDivider
            onPress={() => router.push(RoutePaths.history)}
          />
          <SettingsRow
            icon="stats-chart-outline"
            iconTone="pro"
            label="Аналітика"
            subtitle="Статистика активності та тренди"
            badge={isPremium ? undefined : 'PRO'}
            showDivider
            onPress={() =>
              isPremium
                ? router.push(RoutePaths.analytics)
                : openPaywall({ source: 'profile', lockedFeature: 'ai_summary' })
            }
          />
          <SettingsRow
            icon="flame-outline"
            iconTone="pro"
            label="Теплова карта"
            subtitle="Карта інтенсивності загроз"
            badge={isPremium ? undefined : 'PRO'}
            onPress={() =>
              isPremium
                ? router.push(RoutePaths.heatmap)
                : openPaywall({ source: 'profile', lockedFeature: 'advanced_filters' })
            }
          />
        </SettingsSection>

        <SettingsSection title="Вигляд" subtitle="Тема застосунку та мова інтерфейсу">
          <ProfileThemeRow />
          <SettingsRow
            icon="language-outline"
            label="Мова"
            subtitle="Мова меню та підписів"
            detail="Українська"
            onPress={() => Alert.alert('NEPTUN', 'Наразі доступна лише українська мова інтерфейсу.')}
          />
        </SettingsSection>

        <SettingsSection title="Безпека" subtitle="Укриття поруч і центр безпеки">
          <SettingsRow
            icon="shield-checkmark-outline"
            label="Центр безпеки"
            subtitle="Правила, поради та екстрені дії"
            showDivider
            onPress={() => router.push(RoutePaths.safety)}
          />
          <SettingsRow
            icon="navigate-outline"
            label="Укриття поруч"
            subtitle="Знайти найближчі укриття на карті"
            onPress={() => router.push(RoutePaths.shelters)}
          />
        </SettingsSection>

        <SettingsSection title="Підтримка" subtitle="Звʼязок із командою NEPTUN">
          <SettingsRow
            icon="paper-plane-outline"
            label="Telegram"
            subtitle="Офіційний канал оновлень"
            showDivider
            onPress={() => void openNeptunTelegramChannel('profile')}
          />
          <SettingsRow
            icon="chatbox-ellipses-outline"
            label="Зворотний звʼязок"
            subtitle="Надіслати відгук або повідомити про проблему"
            showDivider
            onPress={() => router.push(RoutePaths.feedback)}
          />
          <SettingsRow
            icon="heart-outline"
            label="Підтримати NEPTUN"
            subtitle="NEPTUN PRO та донат"
            onPress={() => router.push(RoutePaths.premium)}
          />
        </SettingsSection>

        <SettingsSection title="Про застосунок" subtitle="Документи, сайт і версія">
          <SettingsRow
            icon="document-text-outline"
            label="Конфіденційність"
            subtitle="Як ми обробляємо ваші дані"
            showDivider
            onPress={() => void Linking.openURL('https://neptun.in.ua/privacy')}
          />
          <SettingsRow
            icon="reader-outline"
            label="Умови використання"
            subtitle="Правила користування сервісом"
            showDivider
            onPress={() => void Linking.openURL('https://neptun.in.ua/terms')}
          />
          <SettingsRow
            icon="globe-outline"
            label="neptun.in.ua"
            subtitle="Веб-версія та додаткова інформація"
            showDivider
            onPress={() => void Linking.openURL('https://neptun.in.ua')}
          />
          <SettingsRow
            icon="information-circle-outline"
            label="Версія застосунку"
            subtitle="Поточна збірка на пристрої"
            detail={`v${AppConstants.appVersion}`}
          />
        </SettingsSection>

        {isModerator ? (
          <SettingsSection title="Адміністрування" subtitle="Модерація та службові інструменти">
            <SettingsRow
              icon="shield-outline"
              label="Модерація відгуків"
              subtitle="Перегляд і обробка звернень"
              showDivider
              onPress={() => router.push(RoutePaths.feedbackModeration)}
            />
            <SettingsRow
              icon="grid-outline"
              label="Адмін панель"
              subtitle="Керування сервісом"
              showDivider
              onPress={() => router.push(RoutePaths.admin)}
            />
            <SettingsRow
              icon="flag-outline"
              label="Скарги чату"
              subtitle="Скарги користувачів у спільноті"
              onPress={() => router.push(RoutePaths.complaints)}
            />
          </SettingsSection>
        ) : null}

        <DeveloperDiagnosticsSection />

        <ProfileLogoutButton onSignedOut={() => void refreshIdentity()} />
      </ScrollView>
    </View>
  );
}
