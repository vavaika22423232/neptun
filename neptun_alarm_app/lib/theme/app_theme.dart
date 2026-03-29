import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// **Neptun Design System 5.0** — Modern Visual Refresh (2025)
///
/// Philosophy: "Calm Confidence"
/// - Warm dark mode (soft charcoal, not pure black)
/// - Cyan-teal accent (fresh, tech-forward, distinct from generic blue)
/// - Plus Jakarta Sans — modern geometric sans
/// - Depth through subtle gradients, soft shadows, frosted glass
class AppTheme {
  static ThemeData get light => _buildTheme(Brightness.light);
  static ThemeData get dark => _buildTheme(Brightness.dark);

  static ThemeData _buildTheme(Brightness brightness) {
    final isDark = brightness == Brightness.dark;
    final colorScheme = isDark ? _darkColorScheme : _lightColorScheme;

    return ThemeData(
      useMaterial3: true,
      brightness: brightness,
      colorScheme: colorScheme,
      scaffoldBackgroundColor: colorScheme.surface,
      textTheme: _buildTextTheme(isDark),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: isDark
            ? colorScheme.surfaceContainerHighest.withValues(alpha: 0.5)
            : colorScheme.surfaceContainerHighest,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(
            color: colorScheme.outline.withValues(alpha: 0.4),
            width: 1,
          ),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide(color: colorScheme.primary, width: 2),
        ),
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      ),
      dialogTheme: DialogThemeData(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        elevation: isDark ? 0 : 8,
        backgroundColor: colorScheme.surfaceContainer,
      ),
      appBarTheme: AppBarThemeData(
        elevation: 0,
        scrolledUnderElevation: 0,
        surfaceTintColor: Colors.transparent,
        backgroundColor: colorScheme.surface,
        foregroundColor: colorScheme.onSurface,
      ),
      bottomSheetTheme: BottomSheetThemeData(
        shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
        ),
        backgroundColor: colorScheme.surfaceContainer,
      ),
      snackBarTheme: SnackBarThemeData(
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
        ),
        contentTextStyle: GoogleFonts.plusJakartaSans(
          fontSize: 14,
          fontWeight: FontWeight.w500,
          color: colorScheme.onInverseSurface,
        ),
      ),
      cardTheme: CardThemeData(
        elevation: isDark ? 0 : 2,
        shadowColor: isDark ? Colors.transparent : Colors.black.withValues(alpha: 0.06),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(24),
          side: BorderSide(
            color: isDark
                ? const Color(0xFF2A2A32)
                : Colors.black.withValues(alpha: 0.04),
            width: 1,
          ),
        ),
        color: isDark ? const Color(0xFF12121A) : Colors.white,
      ),
      pageTransitionsTheme: const PageTransitionsTheme(
        builders: {
          TargetPlatform.android: ZoomPageTransitionsBuilder(),
          TargetPlatform.iOS: CupertinoPageTransitionsBuilder(),
          TargetPlatform.macOS: CupertinoPageTransitionsBuilder(),
          TargetPlatform.linux: FadeUpwardsPageTransitionsBuilder(),
          TargetPlatform.windows: FadeUpwardsPageTransitionsBuilder(),
        },
      ),
      iconTheme: IconThemeData(
        color: isDark ? const Color(0xFFE8ECF4) : const Color(0xFF1A1D24),
        size: 24,
      ),
      navigationBarTheme: NavigationBarThemeData(
        backgroundColor: isDark ? const Color(0xFF0C0C12) : Colors.white,
        indicatorColor: isDark
            ? const Color(0xFF22D3EE).withValues(alpha: 0.18)
            : const Color(0xFF06B6D4).withValues(alpha: 0.15),
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        height: 68,
        labelBehavior: NavigationDestinationLabelBehavior.alwaysShow,
        iconTheme: WidgetStateProperty.resolveWith((states) {
          if (states.contains(WidgetState.selected)) {
            return IconThemeData(
              color: isDark ? const Color(0xFF22D3EE) : const Color(0xFF0891B2),
              size: 24,
            );
          }
          return IconThemeData(
            color: isDark ? const Color(0xFF6B7280) : const Color(0xFF9CA3AF),
            size: 24,
          );
        }),
        labelTextStyle: WidgetStateProperty.resolveWith((states) {
          final isSelected = states.contains(WidgetState.selected);
          return GoogleFonts.plusJakartaSans(
            fontSize: 11,
            fontWeight: isSelected ? FontWeight.w600 : FontWeight.w500,
            color: isSelected
                ? (isDark ? const Color(0xFF22D3EE) : const Color(0xFF0891B2))
                : (isDark ? const Color(0xFF6B7280) : const Color(0xFF9CA3AF)),
          );
        }),
      ),
    );
  }

  static const ColorScheme _darkColorScheme = ColorScheme(
    brightness: Brightness.dark,
    primary: Color(0xFF22D3EE),
    onPrimary: Color(0xFF0C1220),
    secondary: Color(0xFF22C55E),
    onSecondary: Color(0xFF052E16),
    tertiary: Color(0xFFF59E0B),
    onTertiary: Color(0xFF422006),
    error: Color(0xFFEF4444),
    onError: Colors.white,
    surface: Color(0xFF08090D),
    onSurface: Color(0xFFE8ECF4),
    surfaceContainer: Color(0xFF12121A),
    surfaceContainerHighest: Color(0xFF1E1E28),
    outline: Color(0xFF2A2A32),
    outlineVariant: Color(0xFF3D3D48),
  );

  static const ColorScheme _lightColorScheme = ColorScheme(
    brightness: Brightness.light,
    primary: Color(0xFF0891B2),
    onPrimary: Colors.white,
    secondary: Color(0xFF059669),
    onSecondary: Colors.white,
    tertiary: Color(0xFFD97706),
    onTertiary: Colors.white,
    error: Color(0xFFDC2626),
    onError: Colors.white,
    surface: Color(0xFFF8FAFC),
    onSurface: Color(0xFF0F172A),
    surfaceContainer: Colors.white,
    surfaceContainerHighest: Color(0xFFF1F5F9),
    outline: Color(0xFFE5E7EB),
    outlineVariant: Color(0xFFD1D5DB),
  );

  static TextTheme _buildTextTheme(bool isDark) {
    final baseColor = isDark
        ? const Color(0xFFE8ECF4)
        : const Color(0xFF0F172A);
    final secondaryColor = isDark
        ? const Color(0xFF9CA3AF)
        : const Color(0xFF64748B);
    return TextTheme(
      displayLarge: GoogleFonts.plusJakartaSans(
        fontSize: 56,
        fontWeight: FontWeight.w200,
        color: baseColor,
        letterSpacing: -2,
      ),
      displayMedium: GoogleFonts.plusJakartaSans(
        fontSize: 44,
        fontWeight: FontWeight.w300,
        color: baseColor,
        letterSpacing: -1,
      ),
      displaySmall: GoogleFonts.plusJakartaSans(
        fontSize: 36,
        fontWeight: FontWeight.w400,
        color: baseColor,
        letterSpacing: -0.5,
      ),
      headlineLarge: GoogleFonts.plusJakartaSans(
        fontSize: 32,
        fontWeight: FontWeight.w700,
        color: baseColor,
        letterSpacing: -0.5,
      ),
      headlineMedium: GoogleFonts.plusJakartaSans(
        fontSize: 28,
        fontWeight: FontWeight.w600,
        color: baseColor,
        letterSpacing: -0.5,
      ),
      headlineSmall: GoogleFonts.plusJakartaSans(
        fontSize: 24,
        fontWeight: FontWeight.w600,
        color: baseColor,
      ),
      titleLarge: GoogleFonts.plusJakartaSans(
        fontSize: 20,
        fontWeight: FontWeight.w600,
        color: baseColor,
      ),
      titleMedium: GoogleFonts.plusJakartaSans(
        fontSize: 16,
        fontWeight: FontWeight.w600,
        color: baseColor,
        letterSpacing: 0.1,
      ),
      titleSmall: GoogleFonts.plusJakartaSans(
        fontSize: 14,
        fontWeight: FontWeight.w600,
        color: secondaryColor,
        letterSpacing: 0.1,
      ),
      bodyLarge: GoogleFonts.plusJakartaSans(
        fontSize: 16,
        fontWeight: FontWeight.w400,
        color: baseColor,
        letterSpacing: 0.2,
      ),
      bodyMedium: GoogleFonts.plusJakartaSans(
        fontSize: 14,
        fontWeight: FontWeight.w400,
        color: secondaryColor,
        letterSpacing: 0.2,
      ),
      bodySmall: GoogleFonts.plusJakartaSans(
        fontSize: 12,
        fontWeight: FontWeight.w400,
        color: secondaryColor,
        letterSpacing: 0.3,
      ),
      labelLarge: GoogleFonts.plusJakartaSans(
        fontSize: 14,
        fontWeight: FontWeight.w500,
        color: baseColor,
        letterSpacing: 0.1,
      ),
      labelMedium: GoogleFonts.plusJakartaSans(
        fontSize: 12,
        fontWeight: FontWeight.w500,
        color: secondaryColor,
        letterSpacing: 0.3,
      ),
      labelSmall: GoogleFonts.plusJakartaSans(
        fontSize: 11,
        fontWeight: FontWeight.w500,
        color: secondaryColor,
        letterSpacing: 0.4,
      ),
    );
  }
}

/// Legacy color constants. Prefer [Theme.of(context).colorScheme] instead:
/// - primary, danger -> colorScheme.primary, colorScheme.error
/// - success -> colorScheme.secondary
/// - warning -> colorScheme.tertiary
/// - Surface/background -> colorScheme.surface, surfaceContainer
@Deprecated('Use Theme.of(context).colorScheme for theme-aware colors')
class AppColors {
  // Brand colors — cyan-teal accent (Design 4.0)
  static const Color primary = Color(0xFF22D3EE);
  static const Color primaryLight = Color(0xFF67E8F9);
  static const Color primaryDark = Color(0xFF0891B2);
  static const Color danger = Color(0xFFF87171);
  static const Color warning = Color(0xFFFBBF24);
  static const Color success = Color(0xFF34D399);

  // Light theme brand colors
  static const Color primaryLt = Color(0xFF0891B2);
  static const Color dangerLt = Color(0xFFDC2626);
  static const Color warningLt = Color(0xFFD97706);
  static const Color successLt = Color(0xFF059669);

  // Dark theme surfaces (Design 4.0 — warm charcoal)
  static const Color background = Color(0xFF0C0C12);
  static const Color surface = Color(0xFF12121A);
  static const Color surfaceElevated = Color(0xFF1E1E28);
  static const Color textPrimary = Color(0xFFE8ECF4);
  static const Color textSecondary = Color(0xFF9CA3AF);
  static const Color textHint = Color(0xFF6B7280);
  static const Color border = Color(0xFF2A2A32);
  static const Color borderActive = Color(0xFF3D3D48);

  // Light theme surfaces
  static const Color backgroundLt = Color(0xFFF8FAFC);
  static const Color surfaceLt = Color(0xFFFFFFFF);
  static const Color surfaceElevatedLt = Color(0xFFF1F5F9);
  static const Color textPrimaryLt = Color(0xFF0F172A);
  static const Color textSecondaryLt = Color(0xFF64748B);
  static const Color textHintLt = Color(0xFF9CA3AF);
  static const Color borderLt = Color(0xFFE5E7EB);
  static const Color borderActiveLt = Color(0xFFD1D5DB);
  // Legacy aliases
  static const Color primaryRed = danger;
  static const Color softBlue = primary;
  static const Color softPurple = Color(0xFFBF5AF2);
  static const Color softGreen = success;
  static const Color softPink = Color(0xFFFF375F);
  static const Color darkBackground = background;
  static const Color darkSurface = surface;
  static const Color card = surface;
  static const Color panelBg = surface;
  static const Color panelBorder = border;
  static const Color white = Color(0xFFF0F6FC);
  static const Color textAccent = primary;
  static const Color darkText = textPrimary;
  static const Color successGreen = success;
  static const Color warningYellow = warning;
  static const Color accentYellow = warning;
  static const Color divider = border;
  static const Color normalFill = Color(0xFF171717);
  static const Color alarmFillState = danger;
  static const Color glassCard = Color(0x1FFFFFFF);
  static const Color glassBorderLight = Color(0x19FFFFFF);
  static const Color glassWhite = Color(0x0FFFFFFF);
  static const Color glassBorder = border;
  static const Color darkGlass = surface;
  static const double bentoRadius = 20.0;
  static const Color darkCard = surface;
  static const Color darkDivider = border;
  static const Color kyivGray = textSecondary;
  static const Color kyivBlue = primary;
  static const Color kyivBlueDark = primaryDark;
  static const Color kyivBlueLight = primaryLight;
  static const Color accent = primary;
}
