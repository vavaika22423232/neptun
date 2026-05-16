library;

import 'package:flutter/material.dart';

import '../theme/diary_design.dart';

/// **Neptun design system**
///
/// Спокійний інтерфейс на базі [ColorScheme]: зрозуміла ієрархія, мінімум декоративних шарів.
///
/// ## Принципи
/// - **Один акцент** (primary / статуси) — без паралельних неонових ефектів у тінях і рамках.
/// - **Поверхні**: base → картка/панель → контент; глибина через відступ і легку тінь або обводку, не через каскад градієнтів.
/// - **Статуси**: safe / alarm / offline залишаються чіткими кольорами там, де це семантика, не прикраса.
/// - **Ритм**: шкала 8pt, передбачувані відступи між блоками.
///
/// ## Темна тема — NEPTUN Premium Modern (веб-токени)
/// Токени поверхонь збігаються з [DiaryColors] (`darkBackground` … `darkSurfaceFloat`).
/// - S0: `#0A0E1A`
/// - S1: `#0F1419`
/// - S2: `#1A1F2E`
/// - S3: `#1F2937`

// ═══════════════════════════════════════════════════════════════════════════
// SPACING — 8 / 12 / 16 / 24 / 32 / 48 (consistent rhythm + “air”)
// ═══════════════════════════════════════════════════════════════════════════

class NeptunSpacing {
  NeptunSpacing._();

  static const double xs = 4;
  static const double sm = 8;
  static const double md = 12;
  static const double lg = 16;
  static const double xl = 24;
  static const double xxl = 32;
  static const double xxxl = 48;

  /// Horizontal inset from screen edges (shell content, lists).
  static const double screenHorizontal = 24;

  /// Vertical gap between major sections (e.g. Profile: card → settings → features).
  static const double sectionGap = 32;

  /// Gap between Bento tiles.
  static const double bentoGap = 16;

  /// Відповідає `--radius-card` (1.5rem) у веб-темі.
  static const double bentoRadius = 24;

  /// Gap between a section title and the block below it.
  static const double sectionTitleToContent = 12;

  static const EdgeInsets pagePadding = EdgeInsets.fromLTRB(
    screenHorizontal,
    0,
    screenHorizontal,
    xxxl,
  );

  /// Default inner padding for cards / panels (roomy, readable).
  static const EdgeInsets cardPadding = EdgeInsets.all(20);

  static const EdgeInsets sectionPadding = EdgeInsets.fromLTRB(
    screenHorizontal,
    xl,
    screenHorizontal,
    lg,
  );

  /// List rows: comfortable tap targets + alignment with cards.
  static const EdgeInsets listTilePadding = EdgeInsets.symmetric(
    horizontal: 20,
    vertical: 16,
  );
}

// ═══════════════════════════════════════════════════════════════════════════
// CORNERS
// ═══════════════════════════════════════════════════════════════════════════

class NeptunRadius {
  NeptunRadius._();

  /// `--radius` − 4px (веб sm)
  static const double xs = 8;
  static const double sm = 10;

  /// `--radius` − 2px (веб md)
  static const double md = 14;

  /// `--radius` = 1rem
  static const double lg = 16;

  /// `--radius` + 4px
  static const double xl = 20;
  static const double pill = 999;
}

// ═══════════════════════════════════════════════════════════════════════════
// ELEVATION / DEPTH
// ═══════════════════════════════════════════════════════════════════════════

class NeptunElevation {
  NeptunElevation._();

  static const double surface = 0;
  static const double raised = 2;
  static const double overlay = 8;
  static const double floating = 16;
}

// ═══════════════════════════════════════════════════════════════════════════
// SURFACE COLORS (dark theme primary)
// ═══════════════════════════════════════════════════════════════════════════

class NeptunSurfaces {
  NeptunSurfaces._();

  /// App / page background (S0).
  static const Color s0 = DiaryColors.darkBackground;

  /// Cards / panels (S1).
  static const Color s1 = DiaryColors.darkSurface;

  /// Overlay / inputs (S2).
  static const Color s2 = DiaryColors.darkSurfaceElevated;

  /// Elevated surfaces (S3).
  static const Color s3 = DiaryColors.darkSurfaceFloat;

  static const Color glass = Color(0x18FFFFFF);

  static const Color border = DiaryColors.darkBorder;

  /// Focus ring
  static const Color borderActive = Color(0xFFE2E8F0);
}

// ═══════════════════════════════════════════════════════════════════════════
// LIGHT SURFACES (light-first product; з [DiaryColors])
// ═══════════════════════════════════════════════════════════════════════════

abstract final class NeptunLightSurfaces {
  NeptunLightSurfaces._();

  /// М’який холст сторінки (не чисто білий — cool paper).
  static const Color canvas = DiaryColors.background;

  /// Картки / підняті панелі.
  static const Color elevated = DiaryColors.surface;

  static const Color border = DiaryColors.border;

  static const Color mutedForeground = DiaryColors.muted;
}

// ═══════════════════════════════════════════════════════════════════════════
// STATUS COLORS (семантика тривог / ОК)
// ═══════════════════════════════════════════════════════════════════════════

class NeptunStatus {
  NeptunStatus._();

  /// Non-alarm «OK» — cool gray (no green in chrome).
  static const Color safe = Color(0xFF64748B);

  /// Critical air alert — only strong chromatic exception.
  static const Color alarm = Color(0xFFDC2626);

  /// Попередження / очікування — спокійний amber (не неон).
  static const Color warning = Color(0xFFD97706);
  static const Color muted = Color(0xFF94A3B8);

  /// Icons / secondary emphasis on dark *and* light surfaces (slate-400).
  static const Color accent = Color(0xFF94A3B8);

  /// PRO badges, premium icon fills (pairs with [NeptunGradients.premium]).
  static const Color premium = DiaryColors.premiumGold;
}

// ═══════════════════════════════════════════════════════════════════════════
// GRADIENTS (акценти та преміум — використовувати вибірково)
// ═══════════════════════════════════════════════════════════════════════════

class NeptunGradients {
  NeptunGradients._();

  static const Color _surfaceDark = Color(0xFF0F1419);

  /// PRO purchase CTA — restrained gold (not neon).
  static const LinearGradient premium = LinearGradient(
    colors: [
      DiaryColors.premiumGoldDeep,
      DiaryColors.premiumGold,
    ],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  static const LinearGradient accent = LinearGradient(
    colors: [_surfaceDark, _surfaceDark],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  static const LinearGradient success = LinearGradient(
    colors: [_surfaceDark, _surfaceDark],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  static const LinearGradient danger = LinearGradient(
    colors: [Color(0xFFDC2626), Color(0xFFDC2626)],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  static const LinearGradient glass = LinearGradient(
    colors: [Color(0x0AFFFFFF), Color(0x0AFFFFFF)],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  static const LinearGradient alarm = LinearGradient(
    colors: [Color(0xFFDC2626), Color(0xFFDC2626)],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  static const LinearGradient safe = LinearGradient(
    colors: [_surfaceDark, _surfaceDark],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  );

  static List<Color> get meshDark => [
    DiaryColors.darkBackground,
    const Color(0xFF0F1419),
    DiaryColors.darkSurfaceElevated,
    DiaryColors.darkBackground,
  ];

  static List<Color> get meshLight => [
    DiaryColors.background,
    DiaryColors.surface,
    const Color(0xFFE2E8F0),
    DiaryColors.background,
  ];
}

// ═══════════════════════════════════════════════════════════════════════════
// SHADOWS
// ═══════════════════════════════════════════════════════════════════════════

class NeptunShadows {
  NeptunShadows._();

  /// Diary: no shadows.
  static List<BoxShadow> get low => const [];

  static List<BoxShadow> get soft => const [];

  static List<BoxShadow> get medium => const [];

  static List<BoxShadow> get high => const [];

  static List<BoxShadow> get card => const [];

  static List<BoxShadow> glow(Color color) => const [];
}

// ═══════════════════════════════════════════════════════════════════════════
// TYPOGRAPHY SCALE
// ═══════════════════════════════════════════════════════════════════════════

/// Simple typography scale (6 base styles)
class NeptunTypography {
  NeptunTypography._();

  // Font sizes
  static const double hero = 28; // (legacy alias)
  static const double h1 = 24; // (legacy alias)
  static const double h2 = 18; // (legacy alias)
  static const double h3 = 18; // (legacy alias)
  static const double h4 = 16; // (legacy alias)
  static const double heading = 24; // h1 - main titles
  static const double title = 18; // section titles
  static const double body = 16; // main body text
  static const double bodySmall = 14; // (legacy alias)
  static const double label = 14; // labels, button text
  static const double caption = 12; // secondary text
  static const double micro = 11; // fine print

  // Legacy height aliases
  static const double heightTight = 1.15;
  static const double heightNormal = 1.65;
  static const double heightRelaxed = 1.65;

  // Line heights
  static const double tight = 1.15;
  static const double normal = 1.65;
  static TextStyle get h1Style => const TextStyle(
    fontSize: 24,
    fontWeight: FontWeight.w600,
    height: 1.15,
    letterSpacing: -0.5,
  );

  static TextStyle get h2Style =>
      const TextStyle(fontSize: 18, fontWeight: FontWeight.w600, height: 1.15);

  static TextStyle get h3Style =>
      const TextStyle(fontSize: 18, fontWeight: FontWeight.w600, height: 1.65);

  static TextStyle get h4Style =>
      const TextStyle(fontSize: 16, fontWeight: FontWeight.w600, height: 1.15);

  static TextStyle get bodyStyle =>
      const TextStyle(fontSize: 16, fontWeight: FontWeight.w400, height: 1.65);

  static TextStyle get bodyBoldStyle =>
      const TextStyle(fontSize: 16, fontWeight: FontWeight.w600, height: 1.65);

  static TextStyle get bodySmallStyle =>
      const TextStyle(fontSize: 14, fontWeight: FontWeight.w600, height: 1.65);

  static TextStyle get captionStyle =>
      const TextStyle(fontSize: 12, fontWeight: FontWeight.w400, height: 1.65);

  static TextStyle get microStyle => const TextStyle(
    fontSize: 11,
    fontWeight: FontWeight.w500,
    height: 1.65,
    letterSpacing: 0.5,
  );
}
