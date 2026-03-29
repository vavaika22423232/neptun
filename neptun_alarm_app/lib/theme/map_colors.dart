import 'package:flutter/material.dart';

// Кольори карти з підтримкою світлої та темної теми
class MapColors {
  final bool isDark;

  MapColors({required this.isDark});

  // Фон
  Color get bgMain => isDark ? const Color(0xFF0B0F14) : const Color(0xFFF8FAFC);
  Color get bgGradientMid => isDark ? const Color(0xFF111827) : const Color(0xFFF1F5F9);
  Color get bgGradientEnd => isDark ? const Color(0xFF0F172A) : const Color(0xFFFFFFFF);

  // Області - нормальний стан
  Color get normalFill => isDark ? const Color(0xFF151B23) : const Color(0xFFF1F5F9);
  Color get normalStroke => isDark ? const Color(0xFF334155) : const Color(0xFFCBD5E1);

  // Області - тривога
  Color get alarmFillState => isDark ? const Color(0xFF7F1D1D) : const Color(0xFFFEE2E2);
  Color get alarmStrokeState => isDark ? const Color(0xFFDC2626) : const Color(0xFFFCA5A5);

  // Райони - нормальний стан
  Color get districtNormalFill => Colors.transparent;
  Color get districtNormalStroke => isDark
      ? const Color(0x264F46E5)
      : const Color(0x334F46E5);

  // Райони - тривога
  Color get districtAlarmFill => isDark ? const Color(0xFFB91C1C) : const Color(0xFFEF4444);
  Color get districtAlarmStroke => isDark ? const Color(0xFFFCA5A5) : const Color(0xFFDC2626);

  // Активна тривога (для пульсації)
  Color get alarmActive => const Color(0xFFDC2626);

  // Границі
  Color get borderDark => isDark ? const Color(0xFF1F2937) : const Color(0xFFE2E8F0);

  // Текст
  Color get textPrimary => isDark ? Colors.white : const Color(0xFF0F172A);
  Color get textSecondary => isDark ? const Color(0xFF94A3B8) : const Color(0xFF475569);
  Color get textAccent => isDark ? const Color(0xFF60A5FA) : const Color(0xFF2563EB);

  // Панелі
  Color get panelBg => isDark
      ? const Color(0xFF111827).withValues(alpha: 0.95)
      : const Color(0xFFFFFFFF).withValues(alpha: 0.95);
  Color get panelBorder => isDark ? const Color(0xFF1F2937) : const Color(0xFFE2E8F0);

  // Підписи областей
  Color get labelColor => isDark
      ? Colors.white.withValues(alpha: 0.85)
      : const Color(0xFF0F172A).withValues(alpha: 0.7);
  
  Color get labelShadow => isDark
      ? Colors.black.withValues(alpha: 0.8)
      : const Color(0xFFFFFEFC).withValues(alpha: 0.9);
}
