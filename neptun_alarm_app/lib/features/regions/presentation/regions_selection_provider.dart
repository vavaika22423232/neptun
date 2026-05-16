import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../../config/prefs_keys.dart';
import '../../../data/ukraine_regions.dart';
import '../../../services/notification_service.dart';

/// Єдиний стан обраних регіонів для сповіщень (таб «Регіони» та сервіси).
///
/// Джерело правди: [PrefsKeys.selectedRegions] + синхронізація з [NotificationService].
final regionsSelectionProvider =
    NotifierProvider<RegionsSelectionNotifier, RegionsSelectionState>(
  RegionsSelectionNotifier.new,
);

class RegionsSelectionState {
  const RegionsSelectionState({
    this.isLoading = true,
    this.selected = const {},
  });

  final bool isLoading;
  final Set<String> selected;

  RegionsSelectionState copyWith({
    bool? isLoading,
    Set<String>? selected,
  }) {
    return RegionsSelectionState(
      isLoading: isLoading ?? this.isLoading,
      selected: selected != null
          ? Set<String>.from(selected)
          : Set<String>.from(this.selected),
    );
  }
}

class RegionsSelectionNotifier extends Notifier<RegionsSelectionState> {
  Timer? _debounce;
  bool _persisting = false;

  @override
  RegionsSelectionState build() {
    ref.onDispose(() {
      _debounce?.cancel();
    });
    Future.microtask(_loadFromPrefs);
    return const RegionsSelectionState();
  }

  Future<void> _loadFromPrefs() async {
    final prefs = await SharedPreferences.getInstance();
    final list = prefs.getStringList(PrefsKeys.selectedRegions) ?? [];
    if (!ref.mounted) return;
    state = state.copyWith(isLoading: false, selected: list.toSet());
  }

  /// Підтягнути з prefs (після pull-to-refresh або зміни ззовні).
  Future<void> reload() => _loadFromPrefs();

  void _schedulePersist() {
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 800), _persist);
  }

  Future<void> _persist() async {
    if (_persisting) return;
    _persisting = true;
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setStringList(
        PrefsKeys.selectedRegions,
        state.selected.toList(),
      );
      await NotificationService().updateRegions(state.selected.toList());
    } catch (_) {
      // silent — як у колишньому табі
    } finally {
      _persisting = false;
    }
  }

  void toggleOblast(String oblast, List<String> districts) {
    final next = Set<String>.from(state.selected);
    if (next.contains(oblast)) {
      next.remove(oblast);
      for (final d in districts) {
        next.remove(d);
      }
    } else {
      next.add(oblast);
    }
    state = state.copyWith(selected: next);
    _schedulePersist();
  }

  void toggleDistrict(String district, String oblast, List<String> oblastDistricts) {
    final next = Set<String>.from(state.selected);
    if (next.contains(district)) {
      next.remove(district);
      final hasAny = oblastDistricts.any((d) => next.contains(d));
      if (!hasAny) next.remove(oblast);
    } else {
      next.add(district);
    }
    state = state.copyWith(selected: next);
    _schedulePersist();
  }

  void selectAllUkraine() {
    final next = <String>{};
    for (final o in UkraineRegions.allOblasts) {
      next.add(o['name'] as String);
    }
    for (final districts in UkraineRegions.districtsByOblast.values) {
      next.addAll(districts);
    }
    state = state.copyWith(selected: next);
    _schedulePersist();
  }

  void clearAll() {
    state = state.copyWith(selected: {});
    _schedulePersist();
  }
}
