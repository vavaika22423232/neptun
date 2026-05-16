import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../design/neptun_design.dart';
import 'diary_design.dart';

/// Monochrome «diary» theme. [ColorScheme.error] / [NeptunStatus.alarm] = critical red only.
class AppTheme {
  static ThemeData get light => _buildTheme(Brightness.light);
  static ThemeData get dark => _buildTheme(Brightness.dark);

  static ColorScheme _lightScheme() {
    return const ColorScheme(
      brightness: Brightness.light,
      primary: DiaryColors.primary,
      onPrimary: DiaryColors.onPrimary,
      secondary: DiaryColors.primary,
      onSecondary: DiaryColors.onPrimary,
      tertiary: DiaryColors.muted,
      onTertiary: DiaryColors.onPrimary,
      error: DiaryColors.alarmRed,
      onError: DiaryColors.onPrimary,
      surface: DiaryColors.surface,
      onSurface: DiaryColors.primary,
      onSurfaceVariant: DiaryColors.muted,
      surfaceContainerLowest: DiaryColors.background,
      surfaceContainerLow: DiaryColors.background,
      surfaceContainer: DiaryColors.surface,
      surfaceContainerHigh: DiaryColors.surface,
      surfaceContainerHighest: DiaryColors.border,
      outline: DiaryColors.border,
      outlineVariant: DiaryColors.border,
      shadow: Colors.transparent,
      scrim: Color(0xFF000000),
      inverseSurface: DiaryColors.primary,
      onInverseSurface: DiaryColors.onPrimary,
      primaryContainer: DiaryColors.surface,
      onPrimaryContainer: DiaryColors.primary,
      secondaryContainer: DiaryColors.surface,
      onSecondaryContainer: DiaryColors.primary,
      tertiaryContainer: DiaryColors.border,
      onTertiaryContainer: DiaryColors.primary,
    );
  }

  static ColorScheme _darkScheme() {
    return const ColorScheme(
      brightness: Brightness.dark,
      primary: DiaryColors.darkPrimary,
      onPrimary: DiaryColors.darkOnPrimary,
      secondary: DiaryColors.darkPrimary,
      onSecondary: DiaryColors.darkOnPrimary,
      tertiary: DiaryColors.darkMuted,
      onTertiary: DiaryColors.darkBackground,
      error: DiaryColors.alarmRed,
      onError: DiaryColors.onPrimary,
      surface: DiaryColors.darkSurface,
      onSurface: DiaryColors.darkPrimary,
      onSurfaceVariant: DiaryColors.darkMuted,
      surfaceContainerLowest: DiaryColors.darkBackground,
      surfaceContainerLow: DiaryColors.darkBackground,
      surfaceContainer: DiaryColors.darkSurface,
      surfaceContainerHigh: DiaryColors.darkSurface,
      surfaceContainerHighest: DiaryColors.darkBorder,
      outline: DiaryColors.darkBorder,
      outlineVariant: DiaryColors.darkBorder,
      shadow: Colors.transparent,
      scrim: Color(0xFF000000),
      inverseSurface: DiaryColors.darkPrimary,
      onInverseSurface: DiaryColors.darkBackground,
      primaryContainer: DiaryColors.darkSurface,
      onPrimaryContainer: DiaryColors.darkPrimary,
      secondaryContainer: DiaryColors.darkSurface,
      onSecondaryContainer: DiaryColors.darkPrimary,
      tertiaryContainer: DiaryColors.darkBorder,
      onTertiaryContainer: DiaryColors.darkPrimary,
    );
  }

  static ThemeData _buildTheme(Brightness brightness) {
    final isDark = brightness == Brightness.dark;
    final colorScheme = isDark ? _darkScheme() : _lightScheme();

    final baseText = TextTheme(
      // Main heading (24px, w600, -0.5 spacing)
      headlineLarge: GoogleFonts.plusJakartaSans(
        fontSize: 24,
        fontWeight: FontWeight.w600,
        height: 1.15,
        letterSpacing: -0.5,
        color: colorScheme.onSurface,
      ),
      // Section heading (18px, w600)
      headlineMedium: GoogleFonts.plusJakartaSans(
        fontSize: 18,
        fontWeight: FontWeight.w600,
        height: 1.15,
        color: colorScheme.onSurface,
      ),
      // Main body text (16px, w400)
      bodyLarge: GoogleFonts.plusJakartaSans(
        fontSize: 16,
        fontWeight: FontWeight.w400,
        height: 1.65,
        color: colorScheme.onSurface,
      ),
      // Secondary body text (16px, w400, muted color)
      bodyMedium: GoogleFonts.plusJakartaSans(
        fontSize: 16,
        fontWeight: FontWeight.w400,
        height: 1.65,
        color: colorScheme.onSurfaceVariant,
      ),
      // Labels & button text (14px, w600)
      labelLarge: GoogleFonts.plusJakartaSans(
        fontSize: 14,
        fontWeight: FontWeight.w600,
        color: colorScheme.onSurface,
      ),
      // Caption/secondary labels (12px, w400)
      labelSmall: GoogleFonts.plusJakartaSans(
        fontSize: 12,
        fontWeight: FontWeight.w400,
        height: 1.4,
        color: colorScheme.onSurfaceVariant,
      ),
    );

    return ThemeData(
      useMaterial3: true,
      brightness: brightness,
      colorScheme: colorScheme,
      scaffoldBackgroundColor: isDark
          ? DiaryColors.darkBackground
          : DiaryColors.background,
      textTheme: baseText,
      splashFactory: InkSplash.splashFactory,
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: isDark ? DiaryColors.darkSurface : DiaryColors.background,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(NeptunRadius.md),
          borderSide: const BorderSide(color: DiaryColors.border, width: 1),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(NeptunRadius.md),
          borderSide: BorderSide(
            color: isDark ? DiaryColors.darkBorder : DiaryColors.border,
            width: 1,
          ),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(NeptunRadius.md),
          borderSide: BorderSide(
            color: isDark ? DiaryColors.darkPrimary : DiaryColors.primary,
            width: 1.5,
          ),
        ),
        contentPadding: const EdgeInsets.symmetric(
          horizontal: 20,
          vertical: 16,
        ),
        hintStyle: GoogleFonts.plusJakartaSans(
          fontSize: 16,
          fontWeight: FontWeight.w400,
          color: colorScheme.onSurfaceVariant.withValues(alpha: 0.65),
        ),
      ),
      listTileTheme: ListTileThemeData(
        contentPadding: NeptunSpacing.listTilePadding,
        minVerticalPadding: NeptunSpacing.md,
        horizontalTitleGap: NeptunSpacing.md,
        iconColor: colorScheme.onSurface,
      ),
      dividerTheme: DividerThemeData(
        space: NeptunSpacing.xl,
        thickness: 1,
        color: isDark ? DiaryColors.darkBorder : DiaryColors.border,
      ),
      dialogTheme: DialogThemeData(
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(NeptunRadius.xl),
        ),
        elevation: 0,
        backgroundColor: isDark ? DiaryColors.darkSurface : DiaryColors.surface,
      ),
      appBarTheme: AppBarThemeData(
        elevation: 0,
        scrolledUnderElevation: 0,
        surfaceTintColor: Colors.transparent,
        backgroundColor: isDark
            ? DiaryColors.darkBackground
            : DiaryColors.background,
        foregroundColor: colorScheme.onSurface,
        centerTitle: true,
        titleTextStyle: GoogleFonts.plusJakartaSans(
          fontSize: 24,
          fontWeight: FontWeight.w600,
          letterSpacing: -0.5,
          color: colorScheme.onSurface,
        ),
      ),
      bottomSheetTheme: BottomSheetThemeData(
        shape: const RoundedRectangleBorder(
          borderRadius: BorderRadius.vertical(
            top: Radius.circular(NeptunRadius.xl),
          ),
        ),
        backgroundColor: isDark ? DiaryColors.darkSurface : DiaryColors.surface,
        elevation: 0,
      ),
      snackBarTheme: SnackBarThemeData(
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(NeptunRadius.pill),
        ),
        backgroundColor: DiaryColors.primary,
        contentTextStyle: GoogleFonts.plusJakartaSans(
          fontSize: 16,
          fontWeight: FontWeight.w500,
          color: DiaryColors.onPrimary,
        ),
      ),
      cardTheme: CardThemeData(
        elevation: 0,
        margin: const EdgeInsets.symmetric(
          horizontal: NeptunSpacing.sm,
          vertical: NeptunSpacing.sm,
        ),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(NeptunRadius.lg),
          side: BorderSide(
            color: isDark ? DiaryColors.darkBorder : DiaryColors.border,
            width: 1,
          ),
        ),
        color: isDark ? DiaryColors.darkSurface : DiaryColors.surface,
        clipBehavior: Clip.antiAlias,
      ),
      iconTheme: IconThemeData(color: colorScheme.onSurface, size: 24),
      filledButtonTheme: FilledButtonThemeData(
        style: ButtonStyle(
          minimumSize: WidgetStateProperty.all(const Size(double.infinity, 52)),
          foregroundColor: WidgetStateProperty.all(colorScheme.onPrimary),
          backgroundColor: WidgetStateProperty.all(colorScheme.primary),
          shape: WidgetStateProperty.all(
            RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(NeptunRadius.pill),
            ),
          ),
          elevation: WidgetStateProperty.all(0),
          textStyle: WidgetStateProperty.all(
            GoogleFonts.plusJakartaSans(
              fontSize: 16,
              fontWeight: FontWeight.w600,
            ),
          ),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: ButtonStyle(
          minimumSize: WidgetStateProperty.all(const Size(double.infinity, 52)),
          foregroundColor: WidgetStateProperty.all(colorScheme.onSurface),
          side: WidgetStateProperty.all(
            BorderSide(
              color: isDark ? DiaryColors.darkBorder : DiaryColors.border,
            ),
          ),
          shape: WidgetStateProperty.all(
            RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(NeptunRadius.pill),
            ),
          ),
          elevation: WidgetStateProperty.all(0),
        ),
      ),
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          foregroundColor: colorScheme.onSurface,
          textStyle: GoogleFonts.plusJakartaSans(
            fontSize: 16,
            fontWeight: FontWeight.w600,
          ),
        ),
      ),
      navigationBarTheme: NavigationBarThemeData(
        backgroundColor: isDark
            ? DiaryColors.darkBackground
            : DiaryColors.background,
        indicatorColor: colorScheme.primary,
        surfaceTintColor: Colors.transparent,
        elevation: 0,
        height: 72,
        labelBehavior: NavigationDestinationLabelBehavior.alwaysShow,
        iconTheme: WidgetStateProperty.resolveWith((states) {
          if (states.contains(WidgetState.selected)) {
            return IconThemeData(color: colorScheme.onPrimary, size: 24);
          }
          return IconThemeData(
            color: colorScheme.onSurface.withValues(alpha: 0.45),
            size: 24,
          );
        }),
        labelTextStyle: WidgetStateProperty.resolveWith((states) {
          final isSelected = states.contains(WidgetState.selected);
          return GoogleFonts.plusJakartaSans(
            fontSize: 11,
            fontWeight: isSelected ? FontWeight.w600 : FontWeight.w500,
            letterSpacing: 0.5,
            color: isSelected
                ? colorScheme.primary
                : colorScheme.onSurface.withValues(alpha: 0.45),
          );
        }),
      ),
    );
  }
}
