import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../di/service_locator.dart';

final themeModeProvider =
    NotifierProvider<ThemeModeNotifier, ThemeMode>(ThemeModeNotifier.new);

class ThemeModeNotifier extends Notifier<ThemeMode> {
  @override
  ThemeMode build() {
    final prefs = ref.read(sharedPreferencesProvider);
    final isDark = prefs.getBool('dark_theme') ?? false;
    return isDark ? ThemeMode.dark : ThemeMode.light;
  }

  Future<void> toggle() async {
    final prefs = ref.read(sharedPreferencesProvider);
    final isDark = state == ThemeMode.light;
    await prefs.setBool('dark_theme', isDark);
    state = isDark ? ThemeMode.dark : ThemeMode.light;
  }
}

final sharedPreferencesProvider = Provider<SharedPreferences>((ref) => sl<SharedPreferences>());
