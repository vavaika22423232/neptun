library;

import 'package:flutter/material.dart';

/// **Neptun Tactical Design System**
///
/// Premium dark UI with operational dashboard feeling.
/// Layered surfaces, strong hierarchy, status-driven components.
///
/// ## Design principles
/// - **Layered depth**: Surface 0 (base) → 1 (raised) → 2 (overlay) → 3 (floating)
/// - **Status-first**: Every key state (safe/alarm/offline) has clear visual treatment
/// - **Information density**: Compact without clutter; scannable at a glance
/// - **Tactical identity**: Operational, authoritative, premium
///
/// ## Surface layers (dark theme)
/// - S0: Base background
/// - S1: Cards, panels (slightly elevated)
/// - S2: Overlays, sheets (modal layer)
/// - S3: Floating elements (FAB, status pills)

// ═══════════════════════════════════════════════════════════════════════════
// SPACING
// ═══════════════════════════════════════════════════════════════════════════

class NeptunSpacing {
  NeptunSpacing._();

  static const double xs = 4;
  static const double sm = 8;
  static const double md = 12;
  static const double lg = 16;
  static const double xl = 20;
  static const double xxl = 24;
  static const double xxxl = 32;

  static const EdgeInsets pagePadding = EdgeInsets.fromLTRB(lg, 0, lg, xxxl);
  static const EdgeInsets cardPadding = EdgeInsets.all(lg);
  static const EdgeInsets sectionPadding = EdgeInsets.fromLTRB(lg, xl, lg, lg);

  /// Bento / dashboard tiles (matches tactical card radius in newer UI experiments).
  static const double bentoRadius = 20;

  /// Gap between bento cells in a grid.
  static const double bentoGap = 12;

  /// Default horizontal screen padding for edge-to-edge layouts.
  static const double screenHorizontal = 16;
}

// ═══════════════════════════════════════════════════════════════════════════
// CORNERS
// ═══════════════════════════════════════════════════════════════════════════

class NeptunRadius {
  NeptunRadius._();

  static const double xs = 6;
  static const double sm = 10;
  static const double md = 14;
  static const double lg = 18;
  static const double xl = 22;
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

  /// Base background - deepest layer
  static const Color s0 = Color(0xFF0B1015);

  /// Raised cards, panels
  static const Color s1 = Color(0xFF111821);

  /// Elevated overlays
  static const Color s2 = Color(0xFF151C27);

  /// Floating elements (FAB, pills)
  static const Color s3 = Color(0xFF202636);

  /// Subtle border
  static const Color border = Color(0xFF273142);

  /// Stronger border (active, focus)
  static const Color borderActive = Color(0xFF556071);
}

// ═══════════════════════════════════════════════════════════════════════════
// STATUS COLORS
// ═══════════════════════════════════════════════════════════════════════════

class NeptunStatus {
  NeptunStatus._();

  static const Color safe = Color(0xFF22C55E);
  static const Color alarm = Color(0xFFEF4444);
  static const Color warning = Color(0xFFF59E0B);
  static const Color muted = Color(0xFF64748B);
  static const Color accent = Color(0xFF22D3EE);

  /// PRO / premium affordances (icons, small badges).
  static const Color premium = Color(0xFFDDBB5B);
}

// ═══════════════════════════════════════════════════════════════════════════
// SHADOWS (light surfaces on roadmap / bento)
// ═══════════════════════════════════════════════════════════════════════════

class NeptunShadows {
  NeptunShadows._();

  static const List<BoxShadow> low = [
    BoxShadow(color: Color(0x12000000), blurRadius: 12, offset: Offset(0, 4)),
  ];
}

// ═══════════════════════════════════════════════════════════════════════════
// TYPOGRAPHY SCALE
// ═══════════════════════════════════════════════════════════════════════════

class NeptunTypography {
  NeptunTypography._();

  static const double hero = 28;
  static const double h1 = 22;
  static const double h2 = 18;
  static const double h3 = 16;
  static const double body = 14;
  static const double caption = 12;
  static const double micro = 11;

  /// Default on-surface: light grey (dark theme pages); override with `style: …copyWith(…)`.
  static TextStyle get h1Style => const TextStyle(
    fontSize: h1,
    fontWeight: FontWeight.w700,
    height: 1.2,
    color: Color(0xFFF1F5F9),
  );

  static TextStyle get bodyStyle => const TextStyle(
    fontSize: body,
    fontWeight: FontWeight.w400,
    height: 1.4,
    color: Color(0xFFCBD5E1),
  );
}
