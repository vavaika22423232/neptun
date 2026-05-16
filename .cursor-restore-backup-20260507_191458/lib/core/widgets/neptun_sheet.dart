import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// Unified bottom sheet with consistent handle, radius, and snap points.
class NeptunSheet extends StatelessWidget {
  final Widget child;
  final String? title;
  final List<Widget>? actions;
  final double initialChildSize;
  final double minChildSize;
  final double maxChildSize;
  final bool snap;

  const NeptunSheet({
    super.key,
    required this.child,
    this.title,
    this.actions,
    this.initialChildSize = 0.5,
    this.minChildSize = 0.1,
    this.maxChildSize = 0.9,
    this.snap = true,
  });

  static Future<T?> show<T>({
    required BuildContext context,
    required WidgetBuilder builder,
    bool isScrollControlled = true,
    bool isDismissible = true,
  }) {
    return showModalBottomSheet<T>(
      context: context,
      isScrollControlled: isScrollControlled,
      isDismissible: isDismissible,
      backgroundColor: Colors.transparent,
      builder: builder,
    );
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return DraggableScrollableSheet(
      initialChildSize: initialChildSize,
      minChildSize: minChildSize,
      maxChildSize: maxChildSize,
      snap: snap,
      snapSizes: snap ? [minChildSize, 0.5, maxChildSize] : null,
      builder: (context, scrollController) {
        return Container(
          decoration: BoxDecoration(
            color: isDark ? const Color(0xFF0F1320) : Colors.white,
            borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: 0.2),
                blurRadius: 20,
                offset: const Offset(0, -4),
              ),
            ],
          ),
          child: Column(
            children: [
              // Handle
              Container(
                margin: const EdgeInsets.only(top: 12),
                width: 36,
                height: 4,
                decoration: BoxDecoration(
                  color: isDark
                      ? Colors.white.withValues(alpha: 0.2)
                      : Colors.black.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(2),
                ),
              ),

              // Title bar
              if (title != null || actions != null)
                Padding(
                  padding: const EdgeInsets.fromLTRB(20, 16, 16, 8),
                  child: Row(
                    children: [
                      if (title != null)
                        Expanded(
                          child: Text(
                            title!,
                            style: GoogleFonts.inter(
                              fontSize: 17,
                              fontWeight: FontWeight.w600,
                              color: cs.onSurface,
                            ),
                          ),
                        ),
                      if (actions != null) ...actions!,
                    ],
                  ),
                ),

              // Content
              Expanded(
                child: SingleChildScrollView(
                  controller: scrollController,
                  child: child,
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}
