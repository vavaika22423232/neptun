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
  static const Color s0 = Color(0xFF08090D);

  /// Raised cards, panels
  static const Color s1 = Color(0xFF0E1014);

  /// Elevated overlays
  static const Color s2 = Color(0xFF14171D);

  /// Floating elements (FAB, pills)
  static const Color s3 = Color(0xFF1A1E26);

  /// Subtle border
  static const Color border = Color(0xFF1E232B);

  /// Stronger border (active, focus)
  static const Color borderActive = Color(0xFF2A3140);
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
}
