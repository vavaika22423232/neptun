import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../config/prefs_keys.dart';

/// Пресет кольору бульбашок Pro-теми чату (налаштування з paywall).
class ChatTheme {
  const ChatTheme({
    required this.id,
    required this.name,
    required this.bubbleColor,
  });

  final String id;
  final String name;
  final Color bubbleColor;

  static const String defaultId = 'neptun';

  static final List<ChatTheme> all = [
    const ChatTheme(
      id: 'neptun',
      name: 'Neptun',
      bubbleColor: Color(0xFFB3D4FC),
    ),
    const ChatTheme(
      id: 'ocean',
      name: 'Океан',
      bubbleColor: Color(0xFF1565C0),
    ),
    const ChatTheme(
      id: 'forest',
      name: 'Ліс',
      bubbleColor: Color(0xFF2E7D32),
    ),
    const ChatTheme(
      id: 'sunset',
      name: 'Захід',
      bubbleColor: Color(0xFFE65100),
    ),
    const ChatTheme(
      id: 'lavender',
      name: 'Лаванда',
      bubbleColor: Color(0xFF7E57C2),
    ),
    const ChatTheme(
      id: 'system',
      name: 'Як у системі',
      bubbleColor: Colors.transparent,
    ),
  ];

  static ChatTheme byId(String id) {
    for (final t in all) {
      if (t.id == id) return t;
    }
    return all.firstWhere((t) => t.id == defaultId);
  }
}

/// Pro-кастомізація UI чату (тема бульбашок, аватарка). Дані в SharedPreferences.
class ProCustomizationService {
  ProCustomizationService(this._prefs);

  final SharedPreferences _prefs;

  String get selectedChatThemeId =>
      _prefs.getString(PrefsKeys.proChatThemeId) ?? ChatTheme.defaultId;

  ChatTheme get selectedChatTheme => ChatTheme.byId(selectedChatThemeId);

  Future<void> setChatTheme(String id) async {
    if (!ChatTheme.all.any((t) => t.id == id)) return;
    await _prefs.setString(PrefsKeys.proChatThemeId, id);
  }

  bool get isAnimatedAvatarEnabled =>
      _prefs.getBool(PrefsKeys.proAnimatedAvatar) ?? false;

  Future<void> setAnimatedAvatar(bool enabled) async {
    await _prefs.setBool(PrefsKeys.proAnimatedAvatar, enabled);
  }
}
