/// Централізовані ключі для SharedPreferences
class PrefsKeys {
  PrefsKeys._();

  // ===== Налаштування сповіщень =====
  static const String notificationsEnabled = 'notifications_enabled';
  static const String subscribedRegions = 'subscribed_regions';
  static const String subscribedDistricts = 'subscribed_districts';
  static const String fcmToken = 'fcm_token';
  static const String deviceId = 'device_id';

  // ===== Тема та UI =====
  static const String darkMode = 'dark_theme';
  static const String firstLaunch = 'first_launch';
  static const String welcomeSkipped = 'welcome_skipped';

  // ===== TTS (Text-to-Speech) =====
  static const String ttsEnabled = 'tts_enabled';
  static const String ttsVolume = 'tts_volume';
  static const String ttsLanguage = 'tts_language';

  // ===== Вібрація =====
  static const String vibrationEnabled = 'vibration_enabled';
  static const String vibrationPattern = 'vibration_pattern';

  // ===== Sleep Mode =====
  static const String sleepModeEnabled = 'sleep_mode_enabled';
  static const String sleepModeStart = 'sleep_mode_start';
  static const String sleepModeEnd = 'sleep_mode_end';

  // ===== Premium =====
  static const String isPremium = 'is_premium';
  static const String premiumExpiry = 'premium_expiry';

  // ===== Ads =====
  static const String adFreeUntil = 'ad_free_until';

  // ===== Чат =====
  static const String chatUserId = 'chat_user_id';
  static const String chatNickname = 'chat_nickname';
  static const String chatAgeConfirmed = 'chat_age_confirmed';
  static const String chatRulesAgreed = 'chat_rules_agreed';
  static const String chatLikedMessages = 'chat_liked_messages';
  static const String isChatModerator = 'is_chat_moderator';
  static const String chatOfflineQueue = 'chat_offline_queue';

  // ===== Changelog =====
  static const String changelogLastShownVersion =
      'changelog_last_shown_version';

  // ===== Review =====
  static const String reviewAppLaunchCount = 'app_launch_count';
  static const String reviewFirstLaunchDate = 'first_launch_date';
  static const String reviewHasShownPrompt = 'has_shown_review_prompt';

  // ===== Медична картка =====
  static const String medicalBloodType = 'medical_blood_type';
  static const String medicalAllergies = 'medical_allergies';
  static const String medicalMedications = 'medical_medications';
  static const String medicalEmergencyContact1 = 'medical_emergency_contact_1';
  static const String medicalEmergencyContact2 = 'medical_emergency_contact_2';

  // ===== Тривожна валіза =====
  static const String emergencyBagItems = 'emergency_bag_items';

  // ===== Battery optimization (Xiaomi/Huawei) =====
  static const String batteryOptPromptLastShown = 'battery_opt_prompt_last_shown';

  // ===== Alarm tracking =====
  static const String lastAlarmState = 'last_alarm_state';
  static const String alarmStartTime = 'alarm_start_time';

  // ===== PRO: Custom alarm sound =====
  static const String alarmSoundId = 'pref_alarm_sound_id';
}
