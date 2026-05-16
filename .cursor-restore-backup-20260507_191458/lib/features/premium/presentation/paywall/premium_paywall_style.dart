import 'package:flutter/material.dart';

/// Окрема палітра paywall — не змішуємо з «звичайними» картками додатку.
/// Темна: глибокий void + золото. Світла: теплий папір + чорнило.
@immutable
class PremiumPaywallStyle {
  const PremiumPaywallStyle({
    required this.backgroundTop,
    required this.backgroundMid,
    required this.backgroundBottom,
    required this.auroraGold,
    required this.auroraCool,
    required this.textPrimary,
    required this.textSecondary,
    required this.textTertiary,
    required this.accent,
    required this.accentDeep,
    required this.panel,
    required this.panelBorder,
    required this.hairline,
    required this.ctaText,
    required this.ctaGradient,
    required this.chromeIcon,
    required this.stickyScrim,
  });

  final Color backgroundTop;
  final Color backgroundMid;
  final Color backgroundBottom;
  final Color auroraGold;
  final Color auroraCool;
  final Color textPrimary;
  final Color textSecondary;
  final Color textTertiary;
  final Color accent;
  final Color accentDeep;
  final Color panel;
  final Color panelBorder;
  final Color hairline;
  final Color ctaText;
  final Gradient ctaGradient;
  final Color chromeIcon;
  final Color stickyScrim;

  static PremiumPaywallStyle of(BuildContext context) {
    return Theme.of(context).brightness == Brightness.dark ? dark : light;
  }

  /// Кінематографічний тьмяний paywall.
  static const PremiumPaywallStyle dark = PremiumPaywallStyle(
    backgroundTop: Color(0xFF03050A),
    backgroundMid: Color(0xFF0A0E18),
    backgroundBottom: Color(0xFF060912),
    auroraGold: Color(0x33C9A04A),
    auroraCool: Color(0x18203654),
    textPrimary: Color(0xFFF2F4F8),
    textSecondary: Color(0xFF9AA3B2),
    textTertiary: Color(0xFF6B7280),
    accent: Color(0xFFD4B060),
    accentDeep: Color(0xFF7A5C20),
    panel: Color(0x0FFFFFFF),
    panelBorder: Color(0x14FFFFFF),
    hairline: Color(0x12FFFFFF),
    ctaText: Color(0xFF1A1204),
    ctaGradient: LinearGradient(
      begin: Alignment.topLeft,
      end: Alignment.bottomRight,
      colors: [Color(0xFFE8C97A), Color(0xFFC9A04A), Color(0xFF9A7428)],
    ),
    chromeIcon: Color(0xFFE8D5A8),
    stickyScrim: Color(0xB306090E),
  );

  /// Світлий варіант: спокійний, редакційний.
  static const PremiumPaywallStyle light = PremiumPaywallStyle(
    backgroundTop: Color(0xFFF8F6F1),
    backgroundMid: Color(0xFFF0EBE3),
    backgroundBottom: Color(0xFFE8E2D8),
    auroraGold: Color(0x22C9A04A),
    auroraCool: Color(0x180F172A),
    textPrimary: Color(0xFF121820),
    textSecondary: Color(0xFF4B5568),
    textTertiary: Color(0xFF7A8496),
    accent: Color(0xFF9A7428),
    accentDeep: Color(0xFF6B5218),
    panel: Color(0xE8FFFFFF),
    panelBorder: Color(0x220F172A),
    hairline: Color(0x140F172A),
    ctaText: Color(0xFF1A1204),
    ctaGradient: LinearGradient(
      begin: Alignment.topLeft,
      end: Alignment.bottomRight,
      colors: [Color(0xFFE8C97A), Color(0xFFC9A04A), Color(0xFF8B6914)],
    ),
    chromeIcon: Color(0xFF6B5218),
    stickyScrim: Color(0xD9F8F6F1),
  );
}
