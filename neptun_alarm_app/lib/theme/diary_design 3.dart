import 'package:flutter/material.dart';

/// «Diary» palette: cool slate neutrals + gold premium hints.
/// Chromatic exceptions: [alarmRed] (critical), [premiumGold] for PRO chrome.
abstract final class DiaryColors {
  DiaryColors._();

  // --- Light (clean paper / fog) ---
  static const Color primary = Color(0xFF0F172A);
  static const Color onPrimary = Color(0xFFFFFFFF);
  static const Color surface = Color(0xFFF1F5F9);
  static const Color background = Color(0xFFF8FAFC);
  static const Color border = Color(0xFFE2E8F0);
  static const Color muted = Color(0xFF64748B);

  // --- Dark (nautical slate — aligned with Neptun web tokens S0–S3) ---
  static const Color darkPrimary = Color(0xFFF1F5F9);
  static const Color darkOnPrimary = Color(0xFF0F172A);
  static const Color darkSurface = Color(0xFF0F1419);
  static const Color darkBackground = Color(0xFF0A0E1A);
  /// Between cards and overlays (S2).
  static const Color darkSurfaceElevated = Color(0xFF1A1F2E);
  /// Modals / highest chips (S3).
  static const Color darkSurfaceFloat = Color(0xFF1F2937);
  static const Color darkBorder = Color(0xFF2A3344);
  static const Color darkMuted = Color(0xFF94A3B8);

  /// Only semantic red (air raid / critical).
  static const Color alarmRed = Color(0xFFDC2626);

  /// PRO / premium accents (buttons, badges) — warm gold on dark.
  static const Color premiumGold = Color(0xFFC9A04A);
  static const Color premiumGoldDeep = Color(0xFF8B6914);
}
