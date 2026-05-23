import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../core/pro/pro_features.dart';
import '../../../../services/widget_service.dart';
import '../../../premium/presentation/providers/premium_provider.dart';
import '../../data/radar_repository.dart';
import '../../domain/radar_snapshot.dart';

final radarRepositoryProvider = Provider<RadarRepository>((ref) {
  return RadarRepository();
});

/// Вікно історії маркерів ([ProGate.mapThreatHistoryMinutes]): реагує на [premiumProvider].
final radarMapHistoryMinutesProvider = Provider<int>((ref) {
  ref.watch(premiumProvider.select((s) => s.tier));
  return ProGate.mapThreatHistoryMinutes;
});

/// Стан стрічки Радару: маркери з REST + лічильник тривог (REST + живий SSE з боку UI).
class RadarFeedUiState {
  const RadarFeedUiState({
    this.markers = const [],
    this.activeOblastsUnderAlarm = 0,
    this.isLoading = false,
    this.error,
    this.lastFetchedAt,
    this.isStaleFromCache = false,
  });

  final List<Map<String, dynamic>> markers;
  final int activeOblastsUnderAlarm;

  /// Перше завантаження або поки немає кешу маркерів.
  final bool isLoading;

  final String? error;
  final DateTime? lastFetchedAt;

  /// Показувати банер «збережені дані» (offline / помилка мережі).
  final bool isStaleFromCache;

  bool get showStaleBanner => isStaleFromCache && markers.isNotEmpty;

  RadarFeedUiState asLoadingPreserveData() => RadarFeedUiState(
        markers: markers,
        activeOblastsUnderAlarm: activeOblastsUnderAlarm,
        isLoading: markers.isEmpty,
        error: null,
        lastFetchedAt: lastFetchedAt,
        isStaleFromCache: isStaleFromCache,
      );
}

final radarFeedProvider =
    NotifierProvider<RadarFeedNotifier, RadarFeedUiState>(RadarFeedNotifier.new);

class RadarFeedNotifier extends Notifier<RadarFeedUiState> {
  @override
  RadarFeedUiState build() {
    ref.listen<bool>(premiumProvider.select((s) => s.isPro), (prev, next) {
      if (prev != null && prev != next) {
        unawaited(refresh());
      }
    });
    Future.microtask(refresh);
    return const RadarFeedUiState(isLoading: true);
  }

  /// Оновлення з SSE ([DataStreamService.alarmStream]); викликає вкладка.
  void applyAlarmStreamSnapshot(List<dynamic> rows) {
    final prev = state;
    final n = RadarRepository.countActiveRegionsFromAlarmStream(rows);
    if (prev.activeOblastsUnderAlarm == n) return;
    state = RadarFeedUiState(
      markers: prev.markers,
      activeOblastsUnderAlarm: n,
      isLoading: prev.isLoading,
      error: prev.error,
      lastFetchedAt: prev.lastFetchedAt,
      isStaleFromCache: prev.isStaleFromCache,
    );
  }

  Future<void> refresh() async {
    final minutes = ref.read(radarMapHistoryMinutesProvider);
    state = state.asLoadingPreserveData();
    try {
      final repo = ref.read(radarRepositoryProvider);
      final RadarSnapshot snap = await repo.fetchSnapshot(
        historyMinutes: minutes,
      );
      state = RadarFeedUiState(
        markers: snap.markers,
        activeOblastsUnderAlarm: snap.activeOblastsUnderAlarm,
        isLoading: false,
        error: null,
        lastFetchedAt: snap.fetchedAt,
        isStaleFromCache: snap.fromDiskCache,
      );
      unawaited(
        WidgetService().syncFromRadarSnapshot(
          markers: snap.markers,
          activeOblastsUnderAlarm: snap.activeOblastsUnderAlarm,
        ),
      );
    } catch (e) {
      final prev = state;
      state = RadarFeedUiState(
        markers: prev.markers,
        activeOblastsUnderAlarm: prev.activeOblastsUnderAlarm,
        isLoading: false,
        error: e.toString(),
        lastFetchedAt: prev.lastFetchedAt,
        isStaleFromCache: prev.isStaleFromCache || prev.markers.isNotEmpty,
      );
    }
  }
}
