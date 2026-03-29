import 'package:flutter/foundation.dart';
import 'package:flutter_tts/flutter_tts.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:volume_controller/volume_controller.dart';
import 'dart:io';
import '../config/prefs_keys.dart';

/// Сервіс для голосового озвучування тривог
class TtsService {
  static final TtsService _instance = TtsService._internal();
  factory TtsService() => _instance;
  TtsService._internal();

  FlutterTts? _flutterTts;
  bool _isInitialized = false;
  bool _isEnabled = false;
  double _volume = 1.0;
  double _pitch = 1.0;
  double _speechRate = 0.5;

  // Кеш для уникнення повторів однакових повідомлень
  final Map<String, DateTime> _spokenCache = {};
  static const Duration _cacheDuration = Duration(
    seconds: 45,
  ); // Зменшено з 5 хв для реальних тривог

  bool get isEnabled => _isEnabled;
  double get volume => _volume;
  double get speechRate => _speechRate;
  double get pitch => _pitch;

  Future<void> initialize() async {
    if (_isInitialized) return;

    try {
      _flutterTts = FlutterTts();

      await _flutterTts!.setLanguage('uk-UA');
      await _flutterTts!.setSpeechRate(_speechRate);
      await _flutterTts!.setVolume(_volume);
      await _flutterTts!.setPitch(_pitch);

      if (Platform.isAndroid) {
        await _flutterTts!.setQueueMode(1);
      }

      if (Platform.isIOS) {
        await _flutterTts!.setSharedInstance(true);
        await _flutterTts!.setIosAudioCategory(
          IosTextToSpeechAudioCategory.playback,
          [
            IosTextToSpeechAudioCategoryOptions.allowBluetooth,
            IosTextToSpeechAudioCategoryOptions.allowBluetoothA2DP,
            IosTextToSpeechAudioCategoryOptions.mixWithOthers,
            IosTextToSpeechAudioCategoryOptions.duckOthers,
          ],
          IosTextToSpeechAudioMode.defaultMode,
        );
      }

      VolumeController().showSystemUI = false;
      await _loadSettings();

      _isInitialized = true;
      debugPrint('TTS Service initialized');
    } catch (e) {
      debugPrint('TTS initialization error: $e');
    }
  }

  Future<void> _loadSettings() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      _isEnabled = prefs.getBool(PrefsKeys.ttsEnabled) ?? false;
      _volume = prefs.getDouble('tts_volume') ?? 1.0;
      _speechRate = prefs.getDouble('tts_speech_rate') ?? 0.5;
      _pitch = prefs.getDouble('tts_pitch') ?? 1.0;

      await _flutterTts?.setVolume(_volume);
      await _flutterTts?.setSpeechRate(_speechRate);
      await _flutterTts?.setPitch(_pitch);
      debugPrint('TTS loaded: enabled=$_isEnabled volume=$_volume');
    } catch (e) {
      debugPrint('Error loading TTS settings: $e');
    }
  }

  Future<void> setEnabled(bool enabled) async {
    _isEnabled = enabled;
    final prefs = await SharedPreferences.getInstance();
    final ok = await prefs.setBool(PrefsKeys.ttsEnabled, enabled);
    debugPrint('TTS saved: enabled=$enabled ok=$ok');
  }

  Future<void> setVolume(double volume) async {
    _volume = volume;
    await _flutterTts?.setVolume(volume);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setDouble('tts_volume', volume);
  }

  Future<void> setSpeechRate(double rate) async {
    _speechRate = rate;
    await _flutterTts?.setSpeechRate(rate);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setDouble('tts_speech_rate', rate);
  }

  /// Діагностика: чи TTS ініціалізовано, поточний стан
  ({bool initialized, bool enabled, bool hasEngine}) get diagnostics {
    return (
      initialized: _isInitialized,
      enabled: _isEnabled,
      hasEngine: _flutterTts != null,
    );
  }

  /// Озвучити повідомлення напряму (обходить перевірку isEnabled)
  /// Використовується для foreground сповіщень та SOS
  Future<void> speakDirect(String text) async {
    debugPrint('TTS speakDirect called with: $text');

    if (_flutterTts == null) {
      debugPrint('TTS: Not initialized, initializing now...');
      await initialize();
    }
    if (_flutterTts == null) {
      debugPrint('TTS: Failed to initialize');
      return;
    }

    // Перевіряємо кеш для уникнення повторів
    final cacheKey = text.toLowerCase().trim().replaceAll(
      RegExp(r'[.,!?]'),
      '',
    );
    if (_wasRecentlySpoken(cacheKey)) {
      debugPrint(
        'TTS: Skipping duplicate (cache hit): ${text.substring(0, text.length > 30 ? 30 : text.length)}...',
      );
      return;
    }

    _markAsSpoken(cacheKey);
    debugPrint('TTS: About to speak: $text');
    await _speakWithVolume(text);
    debugPrint('TTS: Finished speaking');
  }

  bool _wasRecentlySpoken(String cacheKey) {
    final lastSpoken = _spokenCache[cacheKey];
    if (lastSpoken == null) return false;
    return DateTime.now().difference(lastSpoken) < _cacheDuration;
  }

  void _markAsSpoken(String cacheKey) {
    _spokenCache[cacheKey] = DateTime.now();
    // Очищаємо старі записи
    final now = DateTime.now();
    _spokenCache.removeWhere(
      (key, time) => now.difference(time) > const Duration(minutes: 10),
    );
  }

  Future<void> _speakWithVolume(String text) async {
    if (_flutterTts == null) return;

    double? previousVolume;

    try {
      if (Platform.isIOS) {
        await _flutterTts!.setSharedInstance(true);
        await _flutterTts!.setIosAudioCategory(
          IosTextToSpeechAudioCategory.playback,
          [
            IosTextToSpeechAudioCategoryOptions.allowBluetooth,
            IosTextToSpeechAudioCategoryOptions.allowBluetoothA2DP,
            IosTextToSpeechAudioCategoryOptions.mixWithOthers,
            IosTextToSpeechAudioCategoryOptions.duckOthers,
          ],
          IosTextToSpeechAudioMode.defaultMode,
        );
      }

      if (Platform.isAndroid) {
        try {
          previousVolume = await VolumeController().getVolume();
          VolumeController().setVolume(_volume, showSystemUI: false);
        } catch (e) {
          if (kDebugMode) debugPrint('VolumeController error: $e');
        }
      }

      await _flutterTts!.setVolume(_volume);
      debugPrint('TTS: Speaking: $text');
      await _flutterTts!.speak(text);
      await _flutterTts!.awaitSpeakCompletion(true);
    } catch (e) {
      debugPrint('TTS speak error: $e');
    } finally {
      if (previousVolume != null) {
        try {
          await Future.delayed(const Duration(milliseconds: 300));
          VolumeController().setVolume(previousVolume, showSystemUI: false);
        } catch (e) {
          debugPrint('VolumeController restore error: $e');
        }
      }
    }
  }

  /// Тестове озвучування
  Future<void> speakTest() async {
    if (_flutterTts == null) return;
    final wasEnabled = _isEnabled;
    _isEnabled = true;
    await _speakWithVolume('Голосові сповіщення працюють!');
    _isEnabled = wasEnabled;
  }

  Future<void> stop() async {
    try {
      await _flutterTts?.stop();
    } catch (e) {
      debugPrint('TTS stop error: $e');
    }
  }
}
