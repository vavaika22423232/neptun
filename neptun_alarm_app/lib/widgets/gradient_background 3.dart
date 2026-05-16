import 'package:flutter/material.dart';

/// Легкий статичний градієнт від [ColorScheme.surface] (без анімації).
class GradientBackground extends StatelessWidget {
  final Widget? child;
  const GradientBackground({super.key, this.child});

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return DecoratedBox(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topCenter,
          end: Alignment.bottomCenter,
          colors: isDark
              ? [
                  cs.surface,
                  Color.lerp(cs.surface, cs.surfaceContainerHighest, 0.35)!,
                ]
              : [
                  cs.surface,
                  Color.lerp(cs.surface, cs.surfaceContainerHighest, 0.5)!,
                ],
        ),
      ),
      child: child,
    );
  }
}
