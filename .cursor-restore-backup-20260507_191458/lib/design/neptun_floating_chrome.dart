import 'dart:ui' show ImageFilter;

import 'package:flutter/material.dart';

import 'backdrop_blur_policy.dart';
import 'neptun_design.dart';

/// Плаваючі панелі (HUD, чат, док): спокійні суцільні поверхні + тонка обводка.
abstract final class NeptunFloatingChrome {
  NeptunFloatingChrome._();

  /// Monochrome badge (legacy name `gold`).
  static const Color gold = Color(0xFF9CA3AF);

  /// Легкий blur для не-shell панелей (chat тощо). Shell — без blur.
  static const double blurSigma = 10;
  /// Верхня панель (назва застосунку + дії) — менше «пігулка», більш прямокутна.
  static const double radiusShell = 18;
  static const double radiusDock = 32;
  static const double radiusChatBar = 28;
  static const double radiusInput = 26;

  static const Color darkTitleOnPanel = Color(0xFFE8EAEF);
  static const Color darkSubtitleOnPanel = Color(0xFF8B93A8);
  static const Color darkIconMuted = Color(0xFFB4BCCA);

  /// Верхній HUD і dock: суцільний колір, одна нейтральна тінь, без кольорових glow.
  static BoxDecoration shellHudDecoration({
    required bool isDark,
    required ColorScheme colorScheme,
    double borderRadius = radiusShell,
    BorderRadius? borderRadiusOverride,
  }) {
    if (!isDark) {
      return panelDecoration(
        isDark: false,
        colorScheme: colorScheme,
        borderRadius: borderRadius,
        borderRadiusOverride: borderRadiusOverride,
      );
    }
    final br = borderRadiusOverride ?? BorderRadius.circular(borderRadius);
    return BoxDecoration(
      borderRadius: br,
      color: NeptunSurfaces.s2,
      border: Border.all(
        color: Colors.white.withValues(alpha: 0.08),
        width: 0.5,
      ),
    );
  }

  static BoxDecoration panelDecoration({
    required bool isDark,
    required ColorScheme colorScheme,
    double borderRadius = radiusShell,
    BorderRadius? borderRadiusOverride,
  }) {
    final br = borderRadiusOverride ?? BorderRadius.circular(borderRadius);
    if (isDark) {
      return BoxDecoration(
        borderRadius: br,
        color: NeptunSurfaces.s2.withValues(alpha: 0.94),
        border: Border.all(
          color: Colors.white.withValues(alpha: 0.085),
          width: 0.5,
        ),
      );
    }
    return BoxDecoration(
      borderRadius: br,
      color: colorScheme.surfaceContainerHighest,
      border: Border.all(
        color: colorScheme.outline.withValues(alpha: 0.12),
        width: 0.5,
      ),
    );
  }
}

/// Обгортка: опційний легкий blur + [panelDecoration] / [shellHudDecoration].
/// Для `shellChrome` blur вимкнено — суцільна панель читається краще.
class NeptunFloatingPanel extends StatelessWidget {
  const NeptunFloatingPanel({
    super.key,
    required this.child,
    this.borderRadius,
    /// Якщо задано, замінює круговий [borderRadius] у декорації та обрізанні.
    this.borderRadiusOverride,
    /// AppShell HUD / dock — без backdrop blur.
    this.shellChrome = false,
  });

  final Widget child;
  final double? borderRadius;
  final BorderRadius? borderRadiusOverride;
  final bool shellChrome;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final cs = Theme.of(context).colorScheme;
    final r = borderRadius ?? NeptunFloatingChrome.radiusShell;
    final decoration = shellChrome
        ? NeptunFloatingChrome.shellHudDecoration(
            isDark: isDark,
            colorScheme: cs,
            borderRadius: r,
            borderRadiusOverride: borderRadiusOverride,
          )
        : NeptunFloatingChrome.panelDecoration(
            isDark: isDark,
            colorScheme: cs,
            borderRadius: r,
            borderRadiusOverride: borderRadiusOverride,
          );

    final panel = DecoratedBox(
      decoration: decoration,
      child: child,
    );

    final skipBlur = shellChrome || neptunSkipBackdropBlur;
    final clipR =
        borderRadiusOverride ?? BorderRadius.circular(r);
    return ClipRRect(
      borderRadius: clipR,
      child: skipBlur
          ? panel
          : BackdropFilter(
              filter: ImageFilter.blur(
                sigmaX: NeptunFloatingChrome.blurSigma,
                sigmaY: NeptunFloatingChrome.blurSigma,
              ),
              child: panel,
            ),
    );
  }
}
