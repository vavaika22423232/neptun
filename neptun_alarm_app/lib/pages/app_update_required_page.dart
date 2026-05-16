import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import 'package:neptun_alarm_app/design/design_exports.dart';
import 'package:neptun_alarm_app/services/app_version_gate_service.dart';
import 'package:neptun_alarm_app/theme/diary_design.dart';
/// Повноекранний блокувальний екран: оновлення обовʼязкове.
class AppUpdateRequiredPage extends StatelessWidget {
  const AppUpdateRequiredPage({
    super.key,
    required this.payload,
  });

  final AppVersionBlockPayload payload;

  Future<void> _openStore(BuildContext context, String url) async {
    final uri = Uri.parse(url);
    try {
      final ok = await launchUrl(uri, mode: LaunchMode.externalApplication);
      if (!ok && context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Не вдалося відкрити посилання')),
        );
      }
    } catch (_) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Не вдалося відкрити посилання')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final accent = NeptunStatus.accent;

    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 20),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const Spacer(),
              Icon(
                Icons.system_update_rounded,
                size: 72,
                color: accent,
              ),
              const SizedBox(height: 24),
              Text(
                payload.title,
                textAlign: TextAlign.center,
                style: NeptunTypography.h1Style.copyWith(
                  fontSize: 26,
                  fontWeight: FontWeight.w800,
                  color: isDark ? DiaryColors.darkPrimary : DiaryColors.primary,
                ),
              ),
              const SizedBox(height: 12),
              Text(
                payload.message,
                textAlign: TextAlign.center,
                style: NeptunTypography.bodyStyle.copyWith(
                  color: isDark ? DiaryColors.darkMuted : DiaryColors.muted,
                  height: 1.45,
                ),
              ),
              const SizedBox(height: 36),
              if (defaultTargetPlatform == TargetPlatform.android)
                FilledButton(
                  onPressed: () => _openStore(context, payload.androidStoreUrl),
                  style: FilledButton.styleFrom(
                    padding: const EdgeInsets.symmetric(vertical: 16),
                    backgroundColor: accent,
                  ),
                  child: const Text('Оновити в Google Play'),
                ),
              if (defaultTargetPlatform == TargetPlatform.iOS)
                FilledButton(
                  onPressed: () => _openStore(context, payload.iosStoreUrl),
                  style: FilledButton.styleFrom(
                    padding: const EdgeInsets.symmetric(vertical: 16),
                    backgroundColor: accent,
                  ),
                  child: const Text('Оновити в App Store'),
                ),
              if (defaultTargetPlatform != TargetPlatform.android &&
                  defaultTargetPlatform != TargetPlatform.iOS) ...[
                FilledButton(
                  onPressed: () => _openStore(context, payload.androidStoreUrl),
                  style: FilledButton.styleFrom(
                    padding: const EdgeInsets.symmetric(vertical: 14),
                    backgroundColor: accent,
                  ),
                  child: const Text('Google Play'),
                ),
                const SizedBox(height: 12),
                OutlinedButton(
                  onPressed: () => _openStore(context, payload.iosStoreUrl),
                  style: OutlinedButton.styleFrom(
                    padding: const EdgeInsets.symmetric(vertical: 14),
                    foregroundColor: accent,
                    side: BorderSide(color: accent.withValues(alpha: 0.5)),
                  ),
                  child: const Text('App Store'),
                ),
              ],
              const Spacer(),
            ],
          ),
        ),
      ),
    );
  }
}
