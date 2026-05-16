import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../design/neptun_design.dart';
import '../services/notification_service.dart';
import '../services/tts_service.dart';
import 'profile_nav_tile.dart';

/// Три швидкі перемикачі на екрані Профіль (як React ProfileView: Push, Звук, Вібрація).
/// «Звук» = голосові озвучування тривог (TTS) — той самий прапорець, що й «Голосові сповіщення» у повному листі.
class ProfileNotificationQuickCard extends StatefulWidget {
  const ProfileNotificationQuickCard({super.key});

  @override
  State<ProfileNotificationQuickCard> createState() =>
      _ProfileNotificationQuickCardState();
}

class _ProfileNotificationQuickCardState
    extends State<ProfileNotificationQuickCard> {
  bool _loading = true;
  bool _notificationsEnabled = true;
  bool _ttsEnabled = false;
  bool _vibrationEnabled = true;

  final TtsService _ttsService = TtsService();

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final prefs = await SharedPreferences.getInstance();
    if (!mounted) return;
    setState(() {
      _notificationsEnabled = prefs.getBool('notifications_enabled') ?? true;
      _ttsEnabled = prefs.getBool('tts_enabled') ?? false;
      _vibrationEnabled = prefs.getBool('vibration_enabled') ?? true;
      _loading = false;
    });
  }

  Future<void> _saveNotifications(bool value) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('notifications_enabled', value);
  }

  Future<void> _saveVibration(bool value) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('vibration_enabled', value);
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const SizedBox(height: 120);
    }

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        ProfileNavTile(
          icon: Icons.notifications_active_rounded,
          label: 'Push-сповіщення',
          subtitle: 'Отримувати сповіщення про тривоги',
          iconAccent: NeptunStatus.accent,
          showDividerBelow: true,
          trailing: Switch.adaptive(
            value: _notificationsEnabled,
            onChanged: (value) {
              setState(() => _notificationsEnabled = value);
              NotificationService().setNotificationsEnabled(value);
              _saveNotifications(value);
            },
          ),
        ),
        ProfileNavTile(
          icon: Icons.volume_up_rounded,
          label: 'Звук',
          subtitle: 'Голосове оповіщення про тривоги (TTS)',
          iconAccent: NeptunStatus.safe,
          showDividerBelow: true,
          trailing: Switch.adaptive(
            value: _ttsEnabled,
            onChanged: (value) async {
              HapticFeedback.lightImpact();
              setState(() => _ttsEnabled = value);
              await _ttsService.setEnabled(value);
            },
          ),
        ),
        ProfileNavTile(
          icon: Icons.vibration_rounded,
          label: 'Вібрація',
          subtitle: 'Вібраційне оповіщення',
          iconAccent: NeptunStatus.premium,
          trailing: Switch.adaptive(
            value: _vibrationEnabled,
            onChanged: (value) async {
              HapticFeedback.selectionClick();
              setState(() => _vibrationEnabled = value);
              await _saveVibration(value);
            },
          ),
        ),
      ],
    );
  }
}
