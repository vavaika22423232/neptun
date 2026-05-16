import 'package:flutter/material.dart';

/// Нейтральний фон екрана (колір з теми) без анімованих «blob».
class AmbientBackground extends StatelessWidget {
  const AmbientBackground({super.key});

  @override
  Widget build(BuildContext context) {
    return ColoredBox(color: Theme.of(context).colorScheme.surface);
  }
}
