import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../../../config/prefs_keys.dart';
import '../../../../core/di/service_locator.dart';
import '../../domain/radar_quick_filter.dart';

class RadarUiState {
  const RadarUiState({
    this.filter = RadarQuickFilter.all,
    this.searchQuery = '',
    this.searchExpanded = false,
    this.telegramDismissed = false,
    this.newUpdatesCount = 0,
  });

  final RadarQuickFilter filter;
  final String searchQuery;
  final bool searchExpanded;
  final bool telegramDismissed;
  final int newUpdatesCount;

  RadarUiState copyWith({
    RadarQuickFilter? filter,
    String? searchQuery,
    bool? searchExpanded,
    bool? telegramDismissed,
    int? newUpdatesCount,
  }) {
    return RadarUiState(
      filter: filter ?? this.filter,
      searchQuery: searchQuery ?? this.searchQuery,
      searchExpanded: searchExpanded ?? this.searchExpanded,
      telegramDismissed: telegramDismissed ?? this.telegramDismissed,
      newUpdatesCount: newUpdatesCount ?? this.newUpdatesCount,
    );
  }
}

final radarUiProvider =
    NotifierProvider<RadarUiNotifier, RadarUiState>(RadarUiNotifier.new);

class RadarUiNotifier extends Notifier<RadarUiState> {
  @override
  RadarUiState build() {
    final prefs = sl<SharedPreferences>();
    final dismissed =
        prefs.getBool(PrefsKeys.telegramRadarBannerDismissed) ?? false;
    return RadarUiState(telegramDismissed: dismissed);
  }

  void setFilter(RadarQuickFilter f) => state = state.copyWith(filter: f);

  void setSearch(String q) => state = state.copyWith(searchQuery: q);

  void toggleSearch() =>
      state = state.copyWith(searchExpanded: !state.searchExpanded);

  Future<void> dismissTelegram() async {
    state = state.copyWith(telegramDismissed: true);
    await sl<SharedPreferences>().setBool(
      PrefsKeys.telegramRadarBannerDismissed,
      true,
    );
  }

  void bumpNewUpdates(int n) {
    if (n <= 0) return;
    state = state.copyWith(newUpdatesCount: state.newUpdatesCount + n);
  }

  void clearNewUpdates() => state = state.copyWith(newUpdatesCount: 0);
}
