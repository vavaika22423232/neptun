import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../core/di/service_locator.dart';
import '../core/pro/pro_features.dart';

class ChatTheme {
  final String id;
  final String name;
  final Color bubbleColor;
  final Color? backgroundColor;
  final String? backgroundPattern;

  const ChatTheme({
    required this.id,
    required this.name,
    required this.bubbleColor,
    this.backgroundColor,
    this.backgroundPattern,
  });

  static const defaultTheme = ChatTheme(
    id: 'default',
    name: 'Стандартна',
    bubbleColor: Colors.transparent, // Uses theme primary
  );

  static const oceanTheme = ChatTheme(
    id: 'ocean',
    name: 'Океан',
    bubbleColor: Color(0xFF0EA5E9),
    backgroundColor: Color(0xFF0C4A6E),
  );

  static const sunsetTheme = ChatTheme(
    id: 'sunset',
    name: 'Захід Сонця',
    bubbleColor: Color(0xFFF43F5E),
    backgroundColor: Color(0xFF450A0A),
  );

  static const forestTheme = ChatTheme(
    id: 'forest',
    name: 'Ліс',
    bubbleColor: Color(0xFF10B981),
    backgroundColor: Color(0xFF064E3B),
  );

  static const all = [defaultTheme, oceanTheme, sunsetTheme, forestTheme];
}

class ProCustomizationService {
  final SharedPreferences _prefs = sl<SharedPreferences>();

  static const _chatThemeKey = 'pro_chat_theme';
  static const _animatedAvatarKey = 'pro_animated_avatar';

  String get selectedChatThemeId => _prefs.getString(_chatThemeKey) ?? 'default';
  
  ChatTheme get selectedChatTheme {
    if (!ProGate.isPro) return ChatTheme.defaultTheme;
    final id = selectedChatThemeId;
    return ChatTheme.all.firstWhere((t) => t.id == id, orElse: () => ChatTheme.defaultTheme);
  }

  bool get isAnimatedAvatarEnabled {
    if (!ProGate.isPro) return false;
    return _prefs.getBool(_animatedAvatarKey) ?? true;
  }

  Future<void> setChatTheme(String themeId) async {
    if (!ProGate.isPro && themeId != ChatTheme.defaultTheme.id) {
      await _prefs.setString(_chatThemeKey, ChatTheme.defaultTheme.id);
      return;
    }
    await _prefs.setString(_chatThemeKey, themeId);
  }

  Future<void> setAnimatedAvatar(bool enabled) async {
    await _prefs.setBool(_animatedAvatarKey, enabled);
  }
}
