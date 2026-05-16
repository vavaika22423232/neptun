import 'package:flutter_tts/flutter_tts.dart';
import 'package:neptun_alarm_app/core/utils/app_debug_log.dart';

/// BCP-47 tags for [Locale.forLanguageTag] / iOS (українська).
const _ukrainianLanguageCandidates = <String>[
  'uk-UA',
  'uk-ua',
  'uk_UA',
  'uk',
];

/// True only for Ukrainian locales (`uk`, `uk-UA`, …), not for arbitrary strings containing "uk".
bool isUkrainianVoiceLocale(String? raw) {
  if (raw == null || raw.isEmpty) return false;
  final n = raw.toLowerCase().replaceAll('_', '-');
  if (n == 'uk') return true;
  if (n.startsWith('uk-')) return true;
  return false;
}

int _rankUkrainianLocale(String locale) {
  final n = locale.toLowerCase().replaceAll('_', '-');
  if (n == 'uk-ua') return 0;
  if (n.startsWith('uk-')) return 1;
  if (n == 'uk') return 2;
  return 3;
}

bool _voiceApplyOk(dynamic result) => result == 1 || result == true;

/// Вибирає український голос зі списку рушія; інакше послідовно пробує [setLanguage].
/// Критично для Android: якщо [setLanguage] не встановив мову (engine лишається EN), озвучка буде не українською.
Future<void> applyUkrainianTtsEngine(FlutterTts tts) async {
  try {
    final voicesRaw = await tts.getVoices;
    if (voicesRaw is List) {
      final candidates = <Map<String, String>>[];
      for (final v in voicesRaw) {
        if (v is! Map) continue;
        final locale = (v['locale'] ?? '').toString();
        if (!isUkrainianVoiceLocale(locale)) continue;
        final name = (v['name'] ?? '').toString();
        if (name.isEmpty) continue;
        candidates.add({'name': name, 'locale': locale});
      }
      candidates.sort((a, b) {
        final c = _rankUkrainianLocale(a['locale']!)
            .compareTo(_rankUkrainianLocale(b['locale']!));
        if (c != 0) return c;
        return a['name']!.compareTo(b['name']!);
      });
      for (final voice in candidates) {
        try {
          final ok = await tts.setVoice({
            'name': voice['name']!,
            'locale': voice['locale']!,
          });
          if (_voiceApplyOk(ok)) {
            appDebugLog(
              '🔊 TTS: Ukrainian voice OK — ${voice['name']} (${voice['locale']})',
            );
            return;
          }
        } catch (e) {
          appDebugLog('🔊 TTS: setVoice failed ${voice['locale']}: $e');
        }
      }
    }
  } catch (e) {
    appDebugLog('🔊 TTS: getVoices error: $e');
  }

  for (final tag in _ukrainianLanguageCandidates) {
    try {
      final res = await tts.setLanguage(tag);
      if (_voiceApplyOk(res)) {
        appDebugLog('🔊 TTS: setLanguage OK — $tag');
        return;
      }
    } catch (e) {
      appDebugLog('🔊 TTS: setLanguage error ($tag): $e');
    }
  }
  appDebugLog(
    '🔊 TTS: WARNING — Ukrainian voice/language unavailable; engine default will be used',
  );
}
