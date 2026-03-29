import 'package:flutter/material.dart';

/// Exposes current bottom nav tab index to descendants (e.g. RadarTab).
/// Used to refresh when user switches to the tab.
class TabIndexScope extends InheritedWidget {
  final int index;

  const TabIndexScope({
    super.key,
    required this.index,
    required super.child,
  });

  static TabIndexScope? maybeOf(BuildContext context) {
    return context.dependOnInheritedWidgetOfExactType<TabIndexScope>();
  }

  @override
  bool updateShouldNotify(TabIndexScope old) => old.index != index;
}
