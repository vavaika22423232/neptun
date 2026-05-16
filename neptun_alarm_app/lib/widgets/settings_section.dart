import 'dart:io';

import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../design/neptun_design.dart';
import '../config/prefs_keys.dart';
import '../core/pro/pro_features.dart';
import '../core/providers/providers.dart';
import '../core/widgets/neptun_card.dart';
import '../core/widgets/neptun_shimmer.dart';
import '../core/widgets/neptun_shell_modal.dart';
import 'profile_nav_tile.dart';
import '../services/android_platform_service.dart';
import '../services/notification_service.dart';
import '../services/sleep_mode_service.dart';
import '../services/tts_service.dart';

/// Inline settings content for ProfileTab (replaces SettingsPage).
/// [omitQuickProfileToggles]: приховати рядки, що дублюють [ProfileNotificationQuickCard] (для bottom sheet).
class SettingsSection extends ConsumerStatefulWidget {
  const SettingsSection({super.key, this.omitQuickProfileToggles = false});

  final bool omitQuickProfileToggles;

  @override
  ConsumerState<SettingsSection> createState() => _SettingsSectionState();
}

class _SettingsSectionState extends ConsumerState<SettingsSection> {
  bool _notificationsEnabled = true;
  bool _darkModeEnabled = false;
  bool _isLoading = true;
  String? _fcmToken;
  String? _apnsToken;
  int _actualSelectionCount = 0;
  List<String> _subscribedTopics = [];

  bool _ttsEnabled = false;
  double _ttsVolume = 1.0;
  bool _sleepModeEnabled = false;
  bool _vibrationEnabled = true;
  String _vibrationPattern = 'auto';
  String _alarmSoundId = 'default';
  bool _showBatteryOptTile = false;

  final TtsService _ttsService = TtsService();
  final SleepModeService _sleepModeService = SleepModeService();

  @override
  void initState() {
    super.initState();
    _loadSettings();
  }

  Future<void> _loadSettings() async {
    final prefs = await SharedPreferences.getInstance();
    final enabled = prefs.getBool('notifications_enabled') ?? true;
    final darkMode = prefs.getBool('dark_theme') ?? false;
    final ttsVolume = prefs.getDouble('tts_volume') ?? 1.0;
    final sleepEnabled = prefs.getBool('sleep_mode_enabled') ?? false;
    final vibEnabled = prefs.getBool('vibration_enabled') ?? true;
    final vibPattern = prefs.getString('vibration_pattern') ?? 'auto';
    final alarmSound = prefs.getString(PrefsKeys.alarmSoundId) ?? 'default';
    final ttsEnabled = prefs.getBool('tts_enabled') ?? false;

    String? token;
    try {
      token = NotificationService().fcmToken;
    } catch (e) {
      token = null;
    }

    String? apns;
    if (Platform.isIOS) {
      try {
        apns = await FirebaseMessaging.instance.getAPNSToken();
      } catch (e) {
        apns = null;
      }
    }

    final topics = prefs.getStringList('subscribed_topics') ?? [];
    final selectedOblastIds = prefs.getStringList('selected_oblast_ids') ?? [];
    final selectedRaionIds = prefs.getStringList('selected_raion_ids') ?? [];
    final actualSelectionCount =
        selectedOblastIds.length + selectedRaionIds.length;

    bool showBatteryOpt = false;
    if (Platform.isAndroid) {
      final android = AndroidPlatformService();
      if (android.needsBatteryOptimizationWarning) {
        showBatteryOpt = !(await android.isBatteryOptimizationDisabled());
      }
    }

    if (mounted) {
      setState(() {
        _notificationsEnabled = enabled;
        _darkModeEnabled = darkMode;
        _ttsEnabled = ttsEnabled;
        _ttsVolume = ttsVolume;
        _sleepModeEnabled = sleepEnabled;
        _vibrationEnabled = vibEnabled;
        _vibrationPattern = vibPattern;
        _alarmSoundId = alarmSound;
        _fcmToken = token;
        _apnsToken = apns;
        _actualSelectionCount = actualSelectionCount;
        _subscribedTopics = topics;
        _showBatteryOptTile = showBatteryOpt;
        _isLoading = false;
      });
    }
  }

  Future<void> _saveSettings() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('notifications_enabled', _notificationsEnabled);
  }

  Future<void> _sendTestNotification() async {
    try {
      await NotificationService().sendTestNotification();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Тестове сповіщення надіслано')),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Помилка: $e')),
        );
      }
    }
  }

  Widget _buildSettingsShimmer(BuildContext context) {
    return const NeptunCard(
      padding: NeptunSpacing.cardPadding,
      child: Row(
        children: [
          NeptunShimmer(width: 22, height: 22, borderRadius: 6),
          SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                NeptunShimmer(width: 120, height: 14, borderRadius: 4),
                SizedBox(height: 6),
                NeptunShimmer(width: 80, height: 12, borderRadius: 4),
              ],
            ),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    if (_isLoading) {
      return Padding(
        padding: NeptunSpacing.cardPadding,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _buildSettingsShimmer(context),
            const SizedBox(height: NeptunSpacing.md),
            _buildSettingsShimmer(context),
            const SizedBox(height: NeptunSpacing.md),
            _buildSettingsShimmer(context),
          ],
        ),
      );
    }

    final isDark = Theme.of(context).brightness == Brightness.dark;

    final omit = widget.omitQuickProfileToggles;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (!omit)
          ProfileNavTile(
            icon: Icons.notifications_active_rounded,
            label: 'Сповіщення',
            subtitle: _notificationsEnabled ? 'Увімкнено' : 'Вимкнено',
            iconAccent: NeptunStatus.accent,
            showDividerBelow: true,
            trailing: Switch.adaptive(
              value: _notificationsEnabled,
              onChanged: (value) {
                setState(() => _notificationsEnabled = value);
                NotificationService().setNotificationsEnabled(value);
                _saveSettings();
              },
            ),
          ),
        ProfileNavTile(
          icon: _darkModeEnabled
              ? Icons.dark_mode_rounded
              : Icons.light_mode_rounded,
          label: 'Темна тема',
          subtitle: _darkModeEnabled ? 'Увімкнено' : 'Вимкнено',
          iconAccent: NeptunStatus.premium,
          showDividerBelow: _fcmToken != null ||
              Platform.isIOS ||
              _actualSelectionCount > 0 ||
              _notificationsEnabled,
          trailing: Switch.adaptive(
            value: _darkModeEnabled,
            onChanged: (value) {
              setState(() => _darkModeEnabled = value);
              ref.read(themeModeProvider.notifier).toggle();
            },
          ),
        ),
        if (_fcmToken != null)
          ProfileNavTile(
            icon: Icons.cloud_done_rounded,
            label: 'Підключено до сервера',
            subtitle: 'Push-сповіщення активні',
            iconAccent: NeptunStatus.safe,
            showDividerBelow: Platform.isIOS || _actualSelectionCount > 0,
          ),
        if (Platform.isIOS)
          ProfileNavTile(
            icon: Icons.phone_iphone_rounded,
            label: 'APNs статус',
            subtitle:
                _apnsToken == null ? 'Токен не отримано' : 'Токен отримано',
            iconAccent: NeptunStatus.accent,
            showDividerBelow: _actualSelectionCount > 0,
          ),
        if (_actualSelectionCount > 0)
          ProfileNavTile(
            icon: Icons.topic_rounded,
            label: 'Підписки на регіони',
            subtitle: 'Активно: $_actualSelectionCount',
            iconAccent: NeptunStatus.warning,
            showDividerBelow: _notificationsEnabled,
          ),
        if (_notificationsEnabled) _buildFcmDiagnosticsTile(isDark),
        if (_notificationsEnabled) const SizedBox(height: NeptunSpacing.lg),
        _sectionHeader('Звук та вібрація', Icons.volume_up_rounded),
        if (!omit || _ttsEnabled)
          NeptunCard(
            padding: NeptunSpacing.cardPadding,
            child: _buildVolumeContent(omitTtsToggle: omit),
          ),
        ProfileNavTile(
          icon: Icons.notifications_active_rounded,
          label: 'Звук тривоги',
          subtitle: _alarmSoundLabels[_alarmSoundId] ?? 'За замовчуванням',
          iconAccent: NeptunStatus.safe,
          showDividerBelow: !omit,
          onTap: () => _showAlarmSoundDialog(isDark),
        ),
        if (!omit)
          ProfileNavTile(
            icon: Icons.vibration_rounded,
            label: 'Вібрація',
            subtitle: _vibrationEnabled
                ? _getVibrationPatternName(_vibrationPattern)
                : 'Вимкнено',
            iconAccent: NeptunStatus.premium,
            trailing: Switch.adaptive(
              value: _vibrationEnabled,
              onChanged: (value) async {
                HapticFeedback.selectionClick();
                setState(() => _vibrationEnabled = value);
                final prefs = await SharedPreferences.getInstance();
                await prefs.setBool('vibration_enabled', value);
              },
            ),
            onTap: () => _showVibrationPatternDialog(isDark),
          ),
        const SizedBox(height: NeptunSpacing.lg),
        _sectionHeader('Режим сну', Icons.bedtime_rounded),
        if (ProGate.isPro)
          NeptunCard(
            padding: NeptunSpacing.cardPadding,
            child: _buildSleepModeContent(isDark),
          )
        else
          NeptunCard(
            padding: NeptunSpacing.cardPadding,
            child: ListTile(
              leading: const Icon(Icons.lock_rounded, color: Colors.amber),
              title: const Text('Режим сну — PRO'),
              subtitle: const Text(
                'Вночі — тиша. Але балістика та ракети все одно розбудять.',
              ),
              trailing: const Icon(Icons.chevron_right_rounded),
              onTap: () => context.push('/premium'),
            ),
          ),
        const SizedBox(height: NeptunSpacing.lg),
        _sectionHeader('Діагностика', Icons.bug_report_rounded),
        if (_showBatteryOptTile)
          ProfileNavTile(
            icon: Icons.battery_alert_rounded,
            label: 'Вимкнути оптимізацію батареї',
            subtitle: 'Для надійних сповіщень на Xiaomi/Huawei',
            iconAccent: NeptunStatus.warning,
            showDividerBelow: true,
            onTap: () {
              HapticFeedback.mediumImpact();
              AndroidPlatformService().requestDisableBatteryOptimization();
            },
          ),
        ProfileNavTile(
          icon: Icons.notifications_none_rounded,
          label: 'Тестове сповіщення',
          subtitle: 'Перевірити доставку',
          iconAccent: NeptunStatus.accent,
          onTap: _sendTestNotification,
        ),
        const SizedBox(height: NeptunSpacing.xl),
      ],
    );
  }

  Widget _buildFcmDiagnosticsTile(bool isDark) {
    final cs = Theme.of(context).colorScheme;
    final topicsStr = _subscribedTopics.isEmpty
        ? 'Немає підписок'
        : _subscribedTopics.take(5).join(', ') +
            (_subscribedTopics.length > 5 ? '…' : '');

    return NeptunCard(
      padding: NeptunSpacing.cardPadding,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.info_outline_rounded, size: 22, color: cs.primary),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Діагностика підписки',
                      style: GoogleFonts.plusJakartaSans(
                        fontSize: 14,
                        fontWeight: FontWeight.w500,
                        color: cs.onSurface,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      'Підписано на: $topicsStr',
                      style: GoogleFonts.plusJakartaSans(
                        fontSize: 12,
                        color: cs.onSurface.withValues(alpha: 0.5),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Text(
            'Якщо сповіщення не приходять: вимкніть оптимізацію батареї для додатку, дозвольте працювати у фоні.',
            style: GoogleFonts.plusJakartaSans(
              fontSize: 11,
              color: cs.onSurface.withValues(alpha: 0.5),
            ),
          ),
        ],
      ),
    );
  }

  Widget _sectionHeader(String title, IconData icon) {
    final cs = Theme.of(context).colorScheme;
    return Padding(
      padding: const EdgeInsets.only(
        top: NeptunSpacing.xl,
        bottom: NeptunSpacing.sm,
        left: NeptunSpacing.xs,
      ),
      child: Row(
        children: [
          Icon(icon, color: cs.onSurface.withValues(alpha: 0.5), size: 18),
          const SizedBox(width: 8),
          Text(
            title,
            style: GoogleFonts.plusJakartaSans(
              fontSize: 14,
              fontWeight: FontWeight.w600,
              color: cs.onSurface.withValues(alpha: 0.5),
              letterSpacing: 0.5,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildVolumeContent({bool omitTtsToggle = false}) {
    final cs = Theme.of(context).colorScheme;

    if (omitTtsToggle && !_ttsEnabled) {
      return const SizedBox.shrink();
    }

    return Column(
        children: [
          if (!omitTtsToggle)
            Row(
              children: [
                Icon(
                  _ttsEnabled
                      ? Icons.record_voice_over_rounded
                      : Icons.voice_over_off_rounded,
                  color: _ttsEnabled
                      ? cs.primary
                      : cs.onSurface.withValues(alpha: 0.4),
                  size: 22,
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Голосові сповіщення',
                        style: GoogleFonts.plusJakartaSans(
                          fontSize: 14,
                          fontWeight: FontWeight.w500,
                          color: cs.onSurface,
                        ),
                      ),
                      const SizedBox(height: 2),
                      Text(
                        _ttsEnabled
                            ? 'Озвучувати тривоги. Увімкніть український голос у налаштуваннях системи (синтез мовлення), інакше можлива інша мова.'
                            : 'Вимкнено',
                        style: GoogleFonts.plusJakartaSans(
                          fontSize: 12,
                          color: cs.onSurface.withValues(alpha: 0.5),
                        ),
                      ),
                    ],
                  ),
                ),
                Switch.adaptive(
                  value: _ttsEnabled,
                  onChanged: (value) async {
                    HapticFeedback.lightImpact();
                    setState(() => _ttsEnabled = value);
                    await _ttsService.setEnabled(value);
                  },
                ),
              ],
            ),
          if (_ttsEnabled) ...[
            if (!omitTtsToggle) const SizedBox(height: 16),
            Row(
              children: [
                Icon(
                  Icons.volume_down_rounded,
                  color: cs.primary.withValues(alpha: 0.7),
                  size: 20,
                ),
                Expanded(
                  child: SliderTheme(
                    data: SliderTheme.of(context).copyWith(
                      activeTrackColor: cs.primary,
                      inactiveTrackColor: cs.primary.withValues(alpha: 0.2),
                      thumbColor: cs.primary,
                      overlayColor: cs.primary.withValues(alpha: 0.2),
                      trackHeight: 6,
                    ),
                    child: Slider(
                      value: _ttsVolume,
                      min: 0.0,
                      max: 1.0,
                      onChanged: (value) async {
                        setState(() => _ttsVolume = value);
                        await _ttsService.setVolume(value);
                      },
                    ),
                  ),
                ),
                Icon(
                  Icons.volume_up_rounded,
                  color: cs.primary,
                  size: 20,
                ),
                const SizedBox(width: 8),
                Text(
                  '${(_ttsVolume * 100).round()}%',
                  style: GoogleFonts.plusJakartaSans(
                    fontWeight: FontWeight.w600,
                    color: cs.primary,
                    fontSize: 14,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Center(
              child: GestureDetector(
                onTap: () {
                  HapticFeedback.lightImpact();
                  _ttsService.initialize();
                  _ttsService.speakTest();
                },
                child: Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 16,
                    vertical: 10,
                  ),
                  decoration: BoxDecoration(
                    color: cs.primary.withValues(alpha: 0.25),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(
                        Icons.play_arrow_rounded,
                        color: cs.onPrimary,
                        size: 20,
                      ),
                      const SizedBox(width: 6),
                      Text(
                        'Тест озвучування',
                        style: GoogleFonts.plusJakartaSans(
                          color: cs.onPrimary,
                          fontWeight: FontWeight.w600,
                          fontSize: 14,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
            const SizedBox(height: 8),
            Builder(
              builder: (context) {
                final d = _ttsService.diagnostics;
                final status = d.initialized && d.hasEngine
                    ? 'Стан голосу: готово'
                    : 'Стан: натисніть «Тест озвучування» для перевірки';
                return Text(
                  status,
                  style: GoogleFonts.plusJakartaSans(
                    fontSize: 12,
                    color: Theme.of(context)
                        .colorScheme
                        .onSurface
                        .withValues(alpha: 0.6),
                  ),
                );
              },
            ),
          ],
        ],
    );
  }

  static const Map<String, String> _alarmSoundLabels = {
    'default': 'За замовчуванням',
    'sharp': 'Різкий',
    'siren': 'Сирена',
  };

  void _showAlarmSoundDialog(bool isDark) {
    final isPro = ProGate.isPro;
    NeptunShellModal.showBottomSheet<void>(
      context: context,
      backgroundColor: Colors.transparent,
      builder: (ctx) => Container(
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surface,
          borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
        ),
        padding: EdgeInsets.all(NeptunSpacing.xl),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Звук тривоги',
              style: GoogleFonts.plusJakartaSans(
                fontSize: 20,
                fontWeight: FontWeight.w700,
                color: Theme.of(context).colorScheme.onSurface,
              ),
            ),
            const SizedBox(height: 16),
            _buildAlarmSoundOption(ctx, 'default', isPro),
            _buildAlarmSoundOption(ctx, 'sharp', isPro),
            _buildAlarmSoundOption(ctx, 'siren', isPro),
          ],
        ),
      ),
    );
  }

  Widget _buildAlarmSoundOption(BuildContext ctx, String id, bool isPro) {
    final label = _alarmSoundLabels[id] ?? id;
    final canSelect = id == 'default' || isPro;
    final selected = _alarmSoundId == id;

    return GestureDetector(
      onTap: () async {
        if (canSelect) {
          setState(() => _alarmSoundId = id);
          final prefs = await SharedPreferences.getInstance();
          await prefs.setString(PrefsKeys.alarmSoundId, id);
          if (ctx.mounted) Navigator.pop(ctx);
        } else {
          Navigator.pop(ctx);
          context.push('/premium');
        }
      },
      child: Container(
        margin: const EdgeInsets.only(bottom: NeptunSpacing.md),
        padding: NeptunSpacing.cardPadding,
        decoration: BoxDecoration(
          color: selected
              ? Theme.of(context).colorScheme.primary.withValues(alpha: 0.15)
              : Theme.of(context)
                  .colorScheme
                  .surfaceContainerHighest
                  .withValues(alpha: 0.5),
          borderRadius: BorderRadius.circular(14),
        ),
        child: Row(
          children: [
            Icon(
              selected
                  ? Icons.check_circle_rounded
                  : Icons.radio_button_unchecked_rounded,
              color: selected
                  ? Theme.of(context).colorScheme.primary
                  : Theme.of(context).colorScheme.onSurface.withValues(alpha: 0.5),
              size: 24,
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Text(
                label,
                style: GoogleFonts.plusJakartaSans(
                  fontSize: 16,
                  color: Theme.of(context).colorScheme.onSurface,
                ),
              ),
            ),
            if (!canSelect) ...[
              Icon(Icons.lock_rounded, size: 18, color: Theme.of(context).colorScheme.tertiary),
              const SizedBox(width: 4),
              Text(
                'PRO',
                style: GoogleFonts.plusJakartaSans(
                  fontSize: 12,
                  fontWeight: FontWeight.w700,
                  color: Theme.of(context).colorScheme.tertiary,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildSleepModeContent(bool isDark) {
    final cs = Theme.of(context).colorScheme;
    final startTime =
        '${_sleepModeService.startHour.toString().padLeft(2, '0')}:${_sleepModeService.startMinute.toString().padLeft(2, '0')}';
    final endTime =
        '${_sleepModeService.endHour.toString().padLeft(2, '0')}:${_sleepModeService.endMinute.toString().padLeft(2, '0')}';

    return Column(
      children: [
        Row(
          children: [
            Icon(
              Icons.bedtime_rounded,
              color: cs.primary,
              size: 22,
            ),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Режим сну',
                    style: GoogleFonts.plusJakartaSans(
                      fontSize: 14,
                      fontWeight: FontWeight.w500,
                      color: cs.onSurface,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    _sleepModeEnabled
                        ? '🌙 $startTime - $endTime'
                        : 'Фільтрація сповіщень вночі',
                    style: GoogleFonts.plusJakartaSans(
                      fontSize: 12,
                      color: cs.onSurface.withValues(alpha: 0.5),
                    ),
                  ),
                ],
              ),
            ),
            Switch.adaptive(
              value: _sleepModeEnabled,
              onChanged: (value) async {
                HapticFeedback.selectionClick();
                setState(() => _sleepModeEnabled = value);
                await _sleepModeService.setEnabled(value);
              },
            ),
          ],
        ),
        if (_sleepModeEnabled) ...[
          const SizedBox(height: 16),
          Divider(height: 1, color: cs.outline.withValues(alpha: 0.3)),
          const SizedBox(height: 16),
          GestureDetector(
            onTap: () => _showSleepTimeDialog(isDark),
            child: Row(
              children: [
                Icon(Icons.schedule_rounded, color: cs.primary, size: 18),
                const SizedBox(width: 8),
                Text(
                  'Час: $startTime - $endTime',
                  style: GoogleFonts.plusJakartaSans(
                    fontSize: 14,
                    color: cs.onSurface,
                    fontWeight: FontWeight.w500,
                  ),
                ),
                const Spacer(),
                Icon(
                  Icons.edit_rounded,
                  color: cs.onSurface.withValues(alpha: 0.5),
                  size: 18,
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              _buildSleepFilterChip(
                '🚀 Ракети',
                _sleepModeService.allowRockets,
                () async {
                  await _sleepModeService.setAlertFilters(
                    rockets: !_sleepModeService.allowRockets,
                  );
                  setState(() {});
                },
              ),
              const SizedBox(width: 8),
              _buildSleepFilterChip(
                '🛩️ Дрони',
                _sleepModeService.allowDrones,
                () async {
                  await _sleepModeService.setAlertFilters(
                    drones: !_sleepModeService.allowDrones,
                  );
                  setState(() {});
                },
              ),
              const SizedBox(width: 8),
              _buildSleepFilterChip(
                '✅ Відбій',
                _sleepModeService.allowAllClear,
                () async {
                  await _sleepModeService.setAlertFilters(
                    allClear: !_sleepModeService.allowAllClear,
                  );
                  setState(() {});
                },
              ),
            ],
          ),
        ],
      ],
    );
  }

  Widget _buildSleepFilterChip(
    String label,
    bool isEnabled,
    VoidCallback onTap,
  ) {
    final cs = Theme.of(context).colorScheme;
    return GestureDetector(
      onTap: () {
        HapticFeedback.selectionClick();
        onTap();
      },
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(
          color: isEnabled
              ? cs.primary.withValues(alpha: 0.15)
              : cs.surfaceContainerHighest.withValues(alpha: 0.5),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: isEnabled ? cs.primary : Colors.transparent,
          ),
        ),
        child: Text(
          label,
          style: GoogleFonts.plusJakartaSans(
            fontSize: 12,
            fontWeight: FontWeight.w500,
            color: isEnabled ? cs.onSurface : cs.onSurface.withValues(alpha: 0.6),
          ),
        ),
      ),
    );
  }

  String _getVibrationPatternName(String pattern) {
    switch (pattern) {
      case 'auto':
        return 'Авто (за типом загрози)';
      case 'strong':
        return 'Сильна';
      case 'light':
        return 'Легка';
      case 'off':
        return 'Вимкнено';
      default:
        return 'Авто';
    }
  }

  void _showVibrationPatternDialog(bool isDark) {
    NeptunShellModal.showBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      builder: (context) => Container(
        padding: NeptunSpacing.cardPadding,
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surfaceContainer,
          borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Center(
              child: Container(
                width: 40,
                height: 4,
                decoration: BoxDecoration(
                  color: Theme.of(context).colorScheme.outline.withValues(alpha: 0.4),
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),
            const SizedBox(height: 20),
            Text(
              'Паттерн вібрації',
              style: GoogleFonts.plusJakartaSans(
                fontSize: 20,
                fontWeight: FontWeight.w700,
                color: Theme.of(context).colorScheme.onSurface,
              ),
            ),
            const SizedBox(height: 16),
            _buildVibrationOption(
              'auto',
              'Авто',
              'Різна вібрація залежно від типу загрози',
              Icons.auto_awesome_rounded,
              isDark,
            ),
            _buildVibrationOption(
              'strong',
              'Сильна',
              'Максимальна вібрація для всіх сповіщень',
              Icons.vibration_rounded,
              isDark,
            ),
            _buildVibrationOption(
              'light',
              'Легка',
              'Делікатна вібрація',
              Icons.touch_app_rounded,
              isDark,
            ),
            _buildVibrationOption(
              'off',
              'Вимкнено',
              'Без вібрації',
              Icons.do_not_disturb_alt_rounded,
              isDark,
            ),
            const SizedBox(height: 16),
          ],
        ),
      ),
    );
  }

  Widget _buildVibrationOption(
    String value,
    String title,
    String subtitle,
    IconData icon,
    bool isDark,
  ) {
    final isSelected = _vibrationPattern == value;
    return GestureDetector(
      onTap: () async {
        final navigator = Navigator.of(context);
        HapticFeedback.selectionClick();
        setState(() => _vibrationPattern = value);
        final prefs = await SharedPreferences.getInstance();
        await prefs.setString('vibration_pattern', value);

        switch (value) {
          case 'strong':
            HapticFeedback.heavyImpact();
            await Future.delayed(const Duration(milliseconds: 100));
            HapticFeedback.heavyImpact();
            await Future.delayed(const Duration(milliseconds: 100));
            HapticFeedback.heavyImpact();
            break;
          case 'light':
            HapticFeedback.lightImpact();
            await Future.delayed(const Duration(milliseconds: 150));
            HapticFeedback.lightImpact();
            break;
          default:
            HapticFeedback.mediumImpact();
            await Future.delayed(const Duration(milliseconds: 200));
            HapticFeedback.mediumImpact();
        }
        if (mounted) navigator.pop();
      },
      child: Container(
        margin: const EdgeInsets.only(bottom: NeptunSpacing.md),
        padding: NeptunSpacing.cardPadding,
        decoration: BoxDecoration(
          color: isSelected
              ? Theme.of(context).colorScheme.primary.withValues(alpha: 0.15)
              : Theme.of(context).colorScheme.surface,
          borderRadius: BorderRadius.circular(16),
          border: isSelected
              ? Border.all(
                  color: Theme.of(context).colorScheme.primary,
                  width: 2,
                )
              : null,
        ),
        child: Row(
          children: [
            Icon(
              icon,
              color: isSelected
                  ? Theme.of(context).colorScheme.primary
                  : Theme.of(context).colorScheme.onSurface.withValues(alpha: 0.4),
              size: 24,
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: GoogleFonts.plusJakartaSans(
                      fontSize: 16,
                      fontWeight: FontWeight.w600,
                      color: Theme.of(context).colorScheme.onSurface,
                    ),
                  ),
                  Text(
                    subtitle,
                    style: GoogleFonts.plusJakartaSans(
                      fontSize: 12,
                      color: Theme.of(context).colorScheme.onSurface.withValues(alpha: 0.6),
                    ),
                  ),
                ],
              ),
            ),
            if (isSelected)
              Icon(
                Icons.check_circle_rounded,
                color: Theme.of(context).colorScheme.primary,
                size: 24,
              ),
          ],
        ),
      ),
    );
  }

  void _showSleepTimeDialog(bool isDark) async {
    int startHour = _sleepModeService.startHour;
    int startMinute = _sleepModeService.startMinute;
    int endHour = _sleepModeService.endHour;
    int endMinute = _sleepModeService.endMinute;

    final result = await NeptunShellModal.showBottomSheet<Map<String, int>>(
      context: context,
      backgroundColor: Colors.transparent,
      isScrollControlled: true,
      builder: (context) => StatefulBuilder(
        builder: (context, setModalState) => Container(
          padding: NeptunSpacing.cardPadding,
          decoration: BoxDecoration(
            color: Theme.of(context).colorScheme.surfaceContainer,
            borderRadius: const BorderRadius.vertical(top: Radius.circular(24)),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Center(
                child: Container(
                  width: 40,
                  height: 4,
                  decoration: BoxDecoration(
                    color: Theme.of(context).colorScheme.outline.withValues(alpha: 0.4),
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              ),
              const SizedBox(height: 20),
              Text(
                'Налаштування режиму сну',
                style: GoogleFonts.plusJakartaSans(
                  fontSize: 20,
                  fontWeight: FontWeight.w700,
                  color: Theme.of(context).colorScheme.onSurface,
                ),
              ),
              const SizedBox(height: 24),
              Row(
                children: [
                  Expanded(
                    child: Column(
                      children: [
                        Text(
                          'Початок',
                          style: GoogleFonts.plusJakartaSans(
                            color: Theme.of(context).colorScheme.onSurface.withValues(alpha: 0.6),
                            fontSize: 13,
                          ),
                        ),
                        const SizedBox(height: 8),
                        GestureDetector(
                          onTap: () async {
                            final time = await showTimePicker(
                              context: context,
                              initialTime: TimeOfDay(
                                hour: startHour,
                                minute: startMinute,
                              ),
                            );
                            if (time != null) {
                              setModalState(() {
                                startHour = time.hour;
                                startMinute = time.minute;
                              });
                            }
                          },
                          child: Container(
                            padding: const EdgeInsets.symmetric(
                              vertical: 16,
                              horizontal: 24,
                            ),
                            decoration: BoxDecoration(
                              color: Theme.of(context).colorScheme.surface,
                              borderRadius: BorderRadius.circular(16),
                            ),
                            child: Text(
                              '${startHour.toString().padLeft(2, '0')}:${startMinute.toString().padLeft(2, '0')}',
                              style: GoogleFonts.plusJakartaSans(
                                fontSize: 24,
                                fontWeight: FontWeight.w700,
                                color: Theme.of(context).colorScheme.primary,
                              ),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 16),
                    child: Icon(
                      Icons.arrow_forward_rounded,
                      color: Theme.of(context).colorScheme.onSurface.withValues(alpha: 0.5),
                    ),
                  ),
                  Expanded(
                    child: Column(
                      children: [
                        Text(
                          'Кінець',
                          style: GoogleFonts.plusJakartaSans(
                            color: Theme.of(context).colorScheme.onSurface.withValues(alpha: 0.6),
                            fontSize: 13,
                          ),
                        ),
                        const SizedBox(height: 8),
                        GestureDetector(
                          onTap: () async {
                            final time = await showTimePicker(
                              context: context,
                              initialTime: TimeOfDay(
                                hour: endHour,
                                minute: endMinute,
                              ),
                            );
                            if (time != null) {
                              setModalState(() {
                                endHour = time.hour;
                                endMinute = time.minute;
                              });
                            }
                          },
                          child: Container(
                            padding: const EdgeInsets.symmetric(
                              vertical: 16,
                              horizontal: 24,
                            ),
                            decoration: BoxDecoration(
                              color: Theme.of(context).colorScheme.surface,
                              borderRadius: BorderRadius.circular(16),
                            ),
                            child: Text(
                              '${endHour.toString().padLeft(2, '0')}:${endMinute.toString().padLeft(2, '0')}',
                              style: GoogleFonts.plusJakartaSans(
                                fontSize: 24,
                                fontWeight: FontWeight.w700,
                                color: Theme.of(context).colorScheme.primary,
                              ),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 24),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  onPressed: () {
                    Navigator.pop(context, {
                      'startHour': startHour,
                      'startMinute': startMinute,
                      'endHour': endHour,
                      'endMinute': endMinute,
                    });
                  },
                  style: ElevatedButton.styleFrom(
                    backgroundColor: Theme.of(context).colorScheme.primary,
                    padding: const EdgeInsets.symmetric(vertical: 16),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(16),
                    ),
                  ),
                  child: Text(
                    'Зберегти',
                    style: GoogleFonts.plusJakartaSans(
                      fontSize: 16,
                      fontWeight: FontWeight.w600,
                      color: Theme.of(context).colorScheme.onPrimary,
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 16),
            ],
          ),
        ),
      ),
    );

    if (result != null) {
      await _sleepModeService.setTimeRange(
        result['startHour']!,
        result['startMinute']!,
        result['endHour']!,
        result['endMinute']!,
      );
      if (mounted) setState(() {});
    }
  }
}
