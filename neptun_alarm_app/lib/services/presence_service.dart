import 'dart:async';
import 'dart:convert';

import 'package:flutter/widgets.dart';
import 'package:http/http.dart' as http;

import '../config/api_config.dart';
import '../config/app_constants.dart';
import 'auth_service.dart';

/// Пінг `/api/presence` з `platform: app` — той самий лічильник, що й на сайті (web + app у Redis).
/// У фоні пінгує рідше, але не зникає з «онлайн», поки процес живий.
class PresenceService with WidgetsBindingObserver {
  PresenceService._();
  static final PresenceService instance = PresenceService._();

  final _totalController = StreamController<int>.broadcast();
  Stream<int> get totalStream => _totalController.stream;

  Timer? _timer;
  bool _started = false;

  void start() {
    if (_started) return;
    _started = true;
    WidgetsBinding.instance.addObserver(this);
    unawaited(_ping());
    _scheduleNextPing();
  }

  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _timer?.cancel();
    _timer = null;
    _started = false;
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.resumed) {
      unawaited(_ping());
    }
    if (_started) _scheduleNextPing();
  }

  Duration _heartbeatDelay() {
    final state = WidgetsBinding.instance.lifecycleState;
    if (state == AppLifecycleState.resumed) {
      return AppConstants.presencePingInterval;
    }
    return AppConstants.presenceBackgroundPingInterval;
  }

  void _scheduleNextPing() {
    _timer?.cancel();
    _timer = Timer(_heartbeatDelay(), () {
      unawaited(_ping());
      if (_started) _scheduleNextPing();
    });
  }

  Future<void> _ping() async {
    try {
      final id = await AuthService.getDeviceId();
      if (id.isEmpty) return;

      final response = await http
          .post(
            Uri.parse(ApiConfig.presence),
            headers: {'Content-Type': 'application/json; charset=utf-8'},
            body: json.encode({'id': id, 'platform': 'app'}),
          )
          .timeout(ApiConfig.httpTimeout);

      if (response.statusCode != 200 || _totalController.isClosed) return;

      final data = json.decode(response.body) as Map<String, dynamic>;
      final total = _parseTotal(data);
      _totalController.add(total);
    } catch (_) {
      /* best-effort */
    }
  }

  static int _parseTotal(Map<String, dynamic> data) {
    final direct = data['total'];
    if (direct is int) return direct;
    if (direct is num) return direct.toInt();
    final web = (data['web'] as num?)?.toInt() ?? 0;
    final apps =
        (data['apps'] as num?)?.toInt() ??
        (data['android'] as num?)?.toInt() ??
        0;
    return web + apps;
  }
}
