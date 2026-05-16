import 'package:flutter/material.dart';

import '../../../../theme/diary_design.dart';

/// Фон чату — ледь помітний вертикальний градієнт для глибини (Neptun / diary tokens).
class ChatBackground extends StatelessWidget {
  const ChatBackground({super.key});

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return SizedBox.expand(
      child: DecoratedBox(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: isDark
                ? [
                    DiaryColors.darkBackground,
                    Color.lerp(
                      DiaryColors.darkBackground,
                      DiaryColors.darkSurfaceElevated,
                      0.35,
                    )!,
                  ]
                : [
                    DiaryColors.background,
                    Color.lerp(
                      DiaryColors.background,
                      DiaryColors.surface,
                      0.55,
                    )!,
                  ],
          ),
        ),
      ),
    );
  }
}
