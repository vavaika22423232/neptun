import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

enum NeptunBadgeType { info, success, warning, danger, pro }

/// Status badge/pill for indicators throughout the app.
class NeptunBadge extends StatelessWidget {
  final String label;
  final NeptunBadgeType type;
  final IconData? icon;
  final bool pulse;

  const NeptunBadge({
    super.key,
    required this.label,
    this.type = NeptunBadgeType.info,
    this.icon,
    this.pulse = false,
  });

  const NeptunBadge.success({
    super.key,
    required this.label,
    this.icon,
    this.pulse = false,
  }) : type = NeptunBadgeType.success;

  const NeptunBadge.warning({
    super.key,
    required this.label,
    this.icon,
    this.pulse = false,
  }) : type = NeptunBadgeType.warning;

  const NeptunBadge.danger({
    super.key,
    required this.label,
    this.icon,
    this.pulse = false,
  }) : type = NeptunBadgeType.danger;

  const NeptunBadge.pro({
    super.key,
    this.label = 'PRO',
    this.icon,
    this.pulse = false,
  }) : type = NeptunBadgeType.pro;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final (Color bg, Color fg) = _colors(isDark);

    Widget badge = Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: fg.withValues(alpha: 0.2), width: 0.5),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (icon != null) ...[
            Icon(icon, size: 12, color: fg),
            const SizedBox(width: 4),
          ],
          Text(
            label,
            style: GoogleFonts.plusJakartaSans(
              fontSize: 11,
              fontWeight: FontWeight.w700,
              color: fg,
              letterSpacing: 0.3,
            ),
          ),
        ],
      ),
    );

    if (pulse) {
      badge = _PulsingWrapper(color: fg, child: badge);
    }

    return badge;
  }

  (Color, Color) _colors(bool isDark) {
    switch (type) {
      case NeptunBadgeType.info:
        return isDark
            ? (const Color(0x264A9EFF), const Color(0xFF4A9EFF))
            : (const Color(0x1A3B82F6), const Color(0xFF3B82F6));
      case NeptunBadgeType.success:
        return isDark
            ? (const Color(0x2632D74B), const Color(0xFF32D74B))
            : (const Color(0x1A22C55E), const Color(0xFF22C55E));
      case NeptunBadgeType.warning:
        return isDark
            ? (const Color(0x26FFD60A), const Color(0xFFFFD60A))
            : (const Color(0x1AF59E0B), const Color(0xFFF59E0B));
      case NeptunBadgeType.danger:
        return isDark
            ? (const Color(0x26FF453A), const Color(0xFFFF453A))
            : (const Color(0x1AEF4444), const Color(0xFFEF4444));
      case NeptunBadgeType.pro:
        return isDark
            ? (const Color(0x26FFB800), const Color(0xFFFFB800))
            : (const Color(0x1AE5A500), const Color(0xFFE5A500));
    }
  }
}

class _PulsingWrapper extends StatefulWidget {
  final Color color;
  final Widget child;
  const _PulsingWrapper({required this.color, required this.child});

  @override
  State<_PulsingWrapper> createState() => _PulsingWrapperState();
}

class _PulsingWrapperState extends State<_PulsingWrapper>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      duration: const Duration(seconds: 2),
      vsync: this,
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _controller,
      builder: (_, child) => Container(
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(6),
          boxShadow: [
            BoxShadow(
              color: widget.color.withValues(alpha: 0.3 * _controller.value),
              blurRadius: 8,
              spreadRadius: 1,
            ),
          ],
        ),
        child: child,
      ),
      child: widget.child,
    );
  }
}
