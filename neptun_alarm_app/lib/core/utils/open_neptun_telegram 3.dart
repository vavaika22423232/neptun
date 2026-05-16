import 'package:firebase_analytics/firebase_analytics.dart';
import 'package:flutter/foundation.dart';
import 'package:url_launcher/url_launcher.dart';

/// Основний invite каналу НЕПТУН у додатку.
const String kNeptunTelegramInviteUrl = 'https://t.me/+Q0PcuV4OkuxmYjVi';

/// Відкрити канал у зовнішньому Telegram і залогувати джерело тапу (CTR / A/B).
///
/// [source]: `app_bar`, `radar_banner`, `profile`, `menu`, `feedback`, `telegram_page`, …
Future<bool> openNeptunTelegramChannel(String source) async {
  if (!kIsWeb) {
    try {
      await FirebaseAnalytics.instance.logEvent(
        name: 'telegram_cta_tap',
        parameters: <String, Object>{'source': source},
      );
    } catch (e, st) {
      assert(() {
        debugPrint('openNeptunTelegram analytics: $e\n$st');
        return true;
      }());
    }
  }

  final uri = Uri.parse(kNeptunTelegramInviteUrl);
  try {
    return await launchUrl(uri, mode: LaunchMode.externalApplication);
  } catch (e, st) {
    assert(() {
      debugPrint('openNeptunTelegram launch: $e\n$st');
      return true;
    }());
    return false;
  }
}
