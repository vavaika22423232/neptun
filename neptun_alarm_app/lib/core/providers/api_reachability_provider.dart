import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:http/http.dart' as http;
import '../../config/api_config.dart';
import '../network/http_retry.dart';
import 'connectivity_provider.dart';

const _checkInterval = Duration(seconds: 45);
const _requestTimeout = Duration(seconds: 5);

/// true = API health endpoint responded OK, false = unreachable or error
final apiReachabilityProvider = StreamProvider.autoDispose<bool>((ref) async* {
  final connectivity = ref.watch(connectivityProvider);
  connectivity.whenData((hasNetwork) {
    if (!hasNetwork) return; // Don't bother checking when no network
  });

  Future<bool> check() async {
    final client = http.Client();
    try {
      final uri = Uri.parse('${ApiConfig.baseUrl}/api/health');
      final res = await httpGetWithRetries(
        client,
        uri,
        timeout: _requestTimeout,
        maxRetries: 2,
      );
      return res.statusCode >= 200 && res.statusCode < 300;
    } catch (e) {
      if (kDebugMode) debugPrint('API reachability check failed: $e');
      return false;
    } finally {
      client.close();
    }
  }

  // Initial check after short delay
  await Future.delayed(const Duration(seconds: 2));
  yield await check();

  await for (final _ in Stream.periodic(_checkInterval)) {
    final hasNetwork = connectivity.value ?? false;
    if (!hasNetwork) {
      yield false;
      continue;
    }
    yield await check();
  }
});

/// Combined: offline = no network OR API unreachable.
/// Use this for OfflineBanner instead of connectivityProvider alone.
enum EffectiveOnlineState {
  online,
  noNetwork,
  apiUnreachable,
}

final effectiveOnlineProvider = Provider<AsyncValue<EffectiveOnlineState>>((ref) {
  final connectivity = ref.watch(connectivityProvider);
  final apiReachability = ref.watch(apiReachabilityProvider);

  return connectivity.when(
    data: (hasNetwork) {
      if (!hasNetwork) {
        return const AsyncData(EffectiveOnlineState.noNetwork);
      }
      return apiReachability.when(
        data: (apiOk) => AsyncData(
          apiOk ? EffectiveOnlineState.online : EffectiveOnlineState.apiUnreachable,
        ),
        loading: () => const AsyncData(EffectiveOnlineState.online),
        error: (_, _) => const AsyncData(EffectiveOnlineState.apiUnreachable),
      );
    },
    loading: () => const AsyncData(EffectiveOnlineState.online),
    error: (_, _) => const AsyncData(EffectiveOnlineState.noNetwork),
  );
});
