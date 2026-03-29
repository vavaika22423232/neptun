import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

bool _isOnline(List<ConnectivityResult> results) {
  if (results.isEmpty) return false;
  return results.any((r) =>
      r == ConnectivityResult.wifi ||
      r == ConnectivityResult.mobile ||
      r == ConnectivityResult.ethernet);
}

/// Провайдер стану мережі. true = є інтернет, false = офлайн.
final connectivityProvider =
    StreamProvider.autoDispose<bool>((ref) async* {
  final initial = await Connectivity().checkConnectivity();
  yield _isOnline(initial);

  yield* Connectivity()
      .onConnectivityChanged
      .map(_isOnline);
});
