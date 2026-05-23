import 'package:flutter/material.dart';

/// Premium Radar tab palette — calm emergency / flight-tracking aesthetic.
abstract final class RadarTokens {
  static const Color bg = Color(0xFF070B12);
  static const Color bgElevated = Color(0xFF0B111A);
  static const Color surface = Color(0xD2121926); // rgba(18,25,38,0.82) approx
  static const Color card = Color(0xFF121A29);
  static const Color border = Color(0x14FFFFFF);
  static const Color accent = Color(0xFF7DD3FC);
  static const Color accentStrong = Color(0xFF38BDF8);
  static const Color live = Color(0xFF34D399);
  static const Color warning = Color(0xFFFBBF24);
  static const Color danger = Color(0xFFFB7185);
  static const Color textPrimary = Color(0xFFF8FAFC);
  static const Color textSecondary = Color(0xFF94A3B8);
  static const Color textMuted = Color(0xFF64748B);

  static const double screenPadH = 20;
  static const double cardPad = 16;
  static const double cardRadius = 24;
  static const double chipRadius = 999;
  static const double sectionGap = 22;
  static const double cardGap = 12;
}
