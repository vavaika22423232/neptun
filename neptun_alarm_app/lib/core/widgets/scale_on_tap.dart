import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

/// Wraps a child with scale-on-tap (0.97) and haptic feedback.
/// Use for tappable cards, buttons, list items.
class ScaleOnTap extends StatefulWidget {
  final Widget child;
  final VoidCallback? onTap;
  final VoidCallback? onLongPress;
  final double scaleDown;

  const ScaleOnTap({
    super.key,
    required this.child,
    this.onTap,
    this.onLongPress,
    this.scaleDown = 0.97,
  });

  @override
  State<ScaleOnTap> createState() => _ScaleOnTapState();
}

class _ScaleOnTapState extends State<ScaleOnTap>
    with SingleTickerProviderStateMixin {
  late AnimationController _ctrl;
  late Animation<double> _scale;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(
      duration: const Duration(milliseconds: 100),
      vsync: this,
    );
    _scale = Tween<double>(
      begin: 1.0,
      end: widget.scaleDown,
    ).animate(CurvedAnimation(parent: _ctrl, curve: Curves.easeInOut));
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  void _onTapDown(TapDownDetails _) {
    _ctrl.forward();
  }

  void _onTapUp(TapUpDetails _) {
    _ctrl.reverse();
  }

  void _onTapCancel() {
    _ctrl.reverse();
  }

  void _onTap() {
    HapticFeedback.lightImpact();
    widget.onTap?.call();
  }

  void _onLongPress() {
    HapticFeedback.mediumImpact();
    widget.onLongPress?.call();
  }

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTapDown: widget.onTap != null || widget.onLongPress != null
          ? _onTapDown
          : null,
      onTapUp: widget.onTap != null || widget.onLongPress != null
          ? _onTapUp
          : null,
      onTapCancel: widget.onTap != null || widget.onLongPress != null
          ? _onTapCancel
          : null,
      onTap: widget.onTap != null ? _onTap : null,
      onLongPress: widget.onLongPress != null ? _onLongPress : null,
      behavior: HitTestBehavior.opaque,
      child: AnimatedBuilder(
        animation: _scale,
        builder: (context, child) {
          return Transform.scale(scale: _scale.value, child: child);
        },
        child: widget.child,
      ),
    );
  }
}
