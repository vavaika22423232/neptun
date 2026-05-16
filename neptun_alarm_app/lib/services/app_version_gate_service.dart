import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import 'package:package_info_plus/package_info_plus.dart';

import 'package:neptun_alarm_app/config/api_config.dart';
import 'package:neptun_alarm_app/config/app_constants.dart';
import 'package:neptun_alarm_app/core/utils/app_debug_log.dart';

/// Дані для екрана «потрібне оновлення».
class AppVersionBlockPayload {
  const AppVersionBlockPayload({
    required this.title,
    required this.message,
    required this.androidStoreUrl,
    required this.iosStoreUrl,
  });

  final String title;
  final String message;
  final String androidStoreUrl;
  final String iosStoreUrl;
}

class AppVersionGateResult {
  const AppVersionGateResult._(this.block);

  final AppVersionBlockPayload? block;

  bool get isBlocked => block != null;

  static const AppVersionGateResult allowed = AppVersionGateResult._(null);

  static AppVersionGateResult blocked(AppVersionBlockPayload payload) =>
      AppVersionGateResult._(payload);
}

/// Політика мінімальної версії з [GET /api/app-requirements].
class AppRequirements {
  const AppRequirements({
    required this.minVersion,
    required this.minBuild,
    required this.title,
    required this.message,
    this.androidStoreUrl,
    this.iosStoreUrl,
  });

  final String minVersion;
  final int minBuild;
  final String title;
  final String message;
  final String? androidStoreUrl;
  final String? iosStoreUrl;

  static AppRequirements? tryParse(Map<String, dynamic> json) {
    try {
      final minVersion = (json['min_version'] as String?)?.trim() ?? '';
      final minBuildRaw = json['min_build'];
      final minBuild = minBuildRaw is int
          ? minBuildRaw
          : int.tryParse('$minBuildRaw') ?? 0;
      final title = (json['title'] as String?)?.trim().isNotEmpty == true
          ? (json['title'] as String).trim()
          : 'Потрібне оновлення';
      final message = (json['message'] as String?)?.trim().isNotEmpty == true
          ? (json['message'] as String).trim()
          : 'Встановіть останню версію додатку, щоб продовжити.';
      return AppRequirements(
        minVersion: minVersion,
        minBuild: minBuild,
        title: title,
        message: message,
        androidStoreUrl: (json['android_store_url'] as String?)?.trim(),
        iosStoreUrl: (json['ios_store_url'] as String?)?.trim(),
      );
    } catch (e) {
      appDebugLog('app-requirements: parse error: $e');
      return null;
    }
  }
}

/// Перевірка мінімальної версії нативного клієнта за відповіддю сервера.
class AppVersionGateService {
  AppVersionGateService._();

  static final AppVersionGateService instance = AppVersionGateService._();

  /// Якщо `false` — при помилці мережі/парсингу доступ заборонено (рідкісний режим).
  static const bool failOpen = bool.fromEnvironment(
    'APP_VERSION_GATE_FAIL_OPEN',
    defaultValue: true,
  );

  Future<AppVersionGateResult> evaluate() async {
    if (kIsWeb) {
      return AppVersionGateResult.allowed;
    }

    PackageInfo info;
    try {
      info = await PackageInfo.fromPlatform();
    } catch (e) {
      appDebugLog('app-version-gate: PackageInfo failed: $e');
      return failOpen
          ? AppVersionGateResult.allowed
          : AppVersionGateResult.blocked(_fallbackPayload());
    }

    final clientVersion = info.version.trim();
    final clientBuild = int.tryParse(info.buildNumber.trim()) ?? 0;

    try {
      final uri = Uri.parse(ApiConfig.appRequirements);
      final response = await http
          .get(uri)
          .timeout(ApiConfig.appRequirementsHttpTimeout);

      if (response.statusCode != 200) {
        appDebugLog(
          'app-version-gate: HTTP ${response.statusCode}',
        );
        return _onFetchError();
      }

      final decoded = jsonDecode(response.body);
      if (decoded is! Map<String, dynamic>) {
        appDebugLog('app-version-gate: expected JSON object');
        return _onFetchError();
      }

      final req = AppRequirements.tryParse(decoded);
      if (req == null) {
        return _onFetchError();
      }

      if (!_isBelowMinimum(
        clientVersion: clientVersion,
        clientBuild: clientBuild,
        req: req,
      )) {
        return AppVersionGateResult.allowed;
      }

      return AppVersionGateResult.blocked(
        AppVersionBlockPayload(
          title: req.title,
          message: req.message,
          androidStoreUrl:
              (req.androidStoreUrl?.isNotEmpty ?? false)
                  ? req.androidStoreUrl!
                  : AppConstants.playStoreListingUrl,
          iosStoreUrl: (req.iosStoreUrl?.isNotEmpty ?? false)
              ? req.iosStoreUrl!
              : AppConstants.appStoreListingUrl,
        ),
      );
    } catch (e) {
      appDebugLog('app-version-gate: $e');
      return _onFetchError();
    }
  }

  AppVersionGateResult _onFetchError() {
    if (failOpen) {
      return AppVersionGateResult.allowed;
    }
    return AppVersionGateResult.blocked(_fallbackPayload());
  }

  AppVersionBlockPayload _fallbackPayload() => AppVersionBlockPayload(
        title: 'Потрібне оновлення',
        message:
            'Не вдалося перевірити версію додатку. Перевірте зʼєднання або оновіть додаток у магазині.',
        androidStoreUrl: AppConstants.playStoreListingUrl,
        iosStoreUrl: AppConstants.appStoreListingUrl,
      );

  static bool _isBelowMinimum({
    required String clientVersion,
    required int clientBuild,
    required AppRequirements req,
  }) {
    if (req.minBuild > 0 && clientBuild < req.minBuild) {
      return true;
    }
    if (req.minVersion.isNotEmpty &&
        _compareSemver(clientVersion, req.minVersion) < 0) {
      return true;
    }
    return false;
  }

  /// Спрощене порівняння semver (лише числові сегменти `major.minor.patch`).
  static int _compareSemver(String a, String b) {
    final pa = _semverCore(a);
    final pb = _semverCore(b);
    final n = pa.length > pb.length ? pa.length : pb.length;
    for (var i = 0; i < n; i++) {
      final va = i < pa.length ? pa[i] : 0;
      final vb = i < pb.length ? pb[i] : 0;
      if (va != vb) {
        return va < vb ? -1 : 1;
      }
    }
    return 0;
  }

  static List<int> _semverCore(String v) {
    final core = v.split('+').first.split('-').first.trim();
    if (core.isEmpty) return const [0];
    return core
        .split('.')
        .map((s) => int.tryParse(s.trim()) ?? 0)
        .toList(growable: false);
  }
}
