/**
 * Mirrors Flutter `lib/config/prefs_keys.dart` for storage parity during migration.
 */
export const PrefsKeys = {
  selectedRegions: 'selected_regions',
  notificationsEnabled: 'notifications_enabled',
  subscribedRegions: 'subscribed_regions',
  subscribedTopics: 'subscribed_topics',
  subscribedDistricts: 'subscribed_districts',
  fcmToken: 'fcm_token',
  deviceId: 'device_id',

  darkMode: 'dark_theme',
  themeMode: 'app_theme_mode',
  firstLaunch: 'first_launch',
  welcomeSkipped: 'welcome_skipped',

  ttsEnabled: 'tts_enabled',
  ttsVolume: 'tts_volume',
  ttsLanguage: 'tts_language',

  vibrationEnabled: 'vibration_enabled',
  vibrationPattern: 'vibration_pattern',

  sleepModeEnabled: 'sleep_mode_enabled',
  sleepModeStart: 'sleep_mode_start',
  sleepModeEnd: 'sleep_mode_end',

  isPremium: 'is_premium',
  premiumExpiry: 'premium_expiry',
  activeTier: 'active_tier',
  debugPremium: 'debug_premium',

  adFreeUntil: 'ad_free_until',
  historyUnlockUntil: 'history_unlock_until',

  chatUserId: 'chat_user_id',
  chatNickname: 'chat_nickname',
  chatAgeConfirmed: 'chat_age_confirmed',
  chatRulesAgreed: 'chat_rules_agreed',
  chatLikedMessages: 'chat_liked_messages',
  isChatModerator: 'is_chat_moderator',
  chatOfflineQueue: 'chat_offline_queue',

  changelogLastShownVersion: 'changelog_last_shown_version',

  reviewAppLaunchCount: 'app_launch_count',
  reviewFirstLaunchDate: 'first_launch_date',
  reviewHasShownPrompt: 'has_shown_review_prompt',

  medicalBloodType: 'medical_blood_type',
  medicalAllergies: 'medical_allergies',
  medicalMedications: 'medical_medications',
  /** Flutter `safety_page.dart` keys */
  emergencyContact1: 'emergency_contact_1',
  emergencyContact2: 'emergency_contact_2',

  emergencyBagItems: 'emergency_bag_items',

  telegramRadarBannerDismissed: 'telegram_radar_banner_dismissed',
  radarSelectedFilter: 'radar_selected_filter',
  radarRecentSearches: 'radar_recent_searches',
  radarFollowedIds: 'radar_followed_ids',
  radarMutedCategories: 'radar_muted_categories',

  batteryOptPromptLastShown: 'battery_opt_prompt_last_shown',

  lastAlarmState: 'last_alarm_state',
  alarmStartTime: 'alarm_start_time',

  alarmSoundId: 'pref_alarm_sound_id',

  /** Flutter `BriefingService._briefingDateKey` */
  briefingLastSentDate: 'briefing_last_sent_date',
} as const;

export type PrefsKey = (typeof PrefsKeys)[keyof typeof PrefsKeys];
