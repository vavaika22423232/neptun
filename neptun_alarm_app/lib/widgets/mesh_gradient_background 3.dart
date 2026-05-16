import 'package:flutter/material.dart';

/// Тихий фон під контент: колір з теми без mesh/blur «ореолів».
class MeshGradientBackground extends StatelessWidget {
  final Widget child;

  const MeshGradientBackground({super.key, required this.child});

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return ColoredBox(
      color: cs.surface,
      child: child,
    );
  }
}
