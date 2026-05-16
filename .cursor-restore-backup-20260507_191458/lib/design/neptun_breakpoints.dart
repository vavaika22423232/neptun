import 'package:flutter/material.dart';

/// Адаптивні колонки для bento-сіток (телефон / планшет).
abstract final class NeptunBreakpoints {
  NeptunBreakpoints._();

  static const double compactMaxWidth = 600;

  static bool isCompact(BuildContext context) =>
      MediaQuery.sizeOf(context).width < compactMaxWidth;

  /// Колонок у bento-сітці: 2 на телефоні, 3 на широкому екрані.
  static int bentoCrossAxisCount(BuildContext context) =>
      isCompact(context) ? 2 : 3;
}
