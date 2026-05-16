import 'package:connectivity_plus/connectivity_plus.dart';

/// True when [results] indicates at least one non-[ConnectivityResult.none] path.
bool connectivityResultsOnline(List<ConnectivityResult> results) {
  if (results.isEmpty) return false;
  return results.any((r) => r != ConnectivityResult.none);
}

/// True, якщо є хоча б одне активне з'єднання (wifi / mobile / ethernet).
Future<bool> isConnectivityOnline() async {
  final results = await Connectivity().checkConnectivity();
  return connectivityResultsOnline(results);
}
