import 'package:flutter/material.dart';
import '../design/neptun_design.dart';
import 'diary_design.dart';

/// Premium Map Colors synced with Neptun Design System (v6.0).
class MapColors {
  final bool isDark;

  MapColors({required this.isDark});

  // Backgrounds
  Color get bgMain => isDark ? NeptunSurfaces.s0 : const Color(0xFFF8FAFC);
  Color get bgGradientMid => isDark ? const Color(0xFF080C14) : const Color(0xFFF1F5F9);
  Color get bgGradientEnd => isDark ? const Color(0xFF0C121D) : const Color(0xFFFFFFFF);

  // States - Oblast
  Color get normalFill => isDark ? const Color(0xFF0F141E) : const Color(0xFFF1F5F9);
  Color get normalStroke => isDark ? const Color(0xFF242C3E) : const Color(0xFFCBD5E1);

  // States - Alarm
  Color get alarmFillState => isDark 
      ? NeptunStatus.alarm.withValues(alpha: 0.18) 
      : NeptunStatus.alarm.withValues(alpha: 0.15);
  Color get alarmStrokeState => NeptunStatus.alarm;

  // Districts
  Color get districtNormalFill => Colors.transparent;
  Color get districtNormalStroke => isDark
      ? const Color(0x204F46E5)
      : const Color(0x264F46E5);

  Color get districtAlarmFill => isDark 
      ? NeptunStatus.alarm.withValues(alpha: 0.35) 
      : NeptunStatus.alarm.withValues(alpha: 0.3);
  Color get districtAlarmStroke => NeptunStatus.alarm;

  // Active alarm pulse
  Color get alarmActive => NeptunStatus.alarm;

  // Borders & Panels
  Color get borderDark => isDark ? const Color(0xFF1F2937) : const Color(0xFFE2E8F0);
  
  Color get panelBg => isDark
      ? DiaryColors.darkSurfaceElevated.withValues(alpha: 0.92)
      : const Color(0xFFFFFFFF).withValues(alpha: 0.9);
  
  Color get panelBorder => isDark 
      ? Colors.white.withValues(alpha: 0.08) 
      : Colors.black.withValues(alpha: 0.05);

  // Text
  Color get textPrimary =>
      isDark ? DiaryColors.darkPrimary : DiaryColors.primary;
  Color get textSecondary => isDark
      ? DiaryColors.darkPrimary.withValues(alpha: 0.55)
      : DiaryColors.muted;
  Color get textAccent => NeptunStatus.accent;

  // Labels
  Color get labelColor => isDark
      ? DiaryColors.darkPrimary.withValues(alpha: 0.92)
      : DiaryColors.primary.withValues(alpha: 0.88);
  
  Color get labelShadow => isDark
      ? Colors.black.withValues(alpha: 0.9)
      : Colors.white.withValues(alpha: 1.0);
}
