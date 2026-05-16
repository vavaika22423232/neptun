import 'package:flutter/material.dart';

import '../../widgets/ambient_background.dart';

/// Спільний каркас для вкладок [AppShell]: [Scaffold] + нейтральний фон.
///
/// Узгоджує «Радар», «Профіль» та інші таби з однаковою базою (не дублювати
/// Stack + [AmbientBackground] у кожному файлі).
class NeptunTabPageScaffold extends StatelessWidget {
  const NeptunTabPageScaffold({
    super.key,
    required this.body,
  });

  /// Зазвичай [RefreshIndicator] + [CustomScrollView] / [ListView].
  final Widget body;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Scaffold(
      backgroundColor: cs.surface,
      body: Stack(
        fit: StackFit.expand,
        children: [
          const AmbientBackground(),
          body,
        ],
      ),
    );
  }
}
