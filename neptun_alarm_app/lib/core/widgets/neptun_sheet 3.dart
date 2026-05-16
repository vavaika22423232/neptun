import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../theme/diary_design.dart';
import '../../design/neptun_design.dart';
import 'neptun_shell_modal.dart';

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
    return NeptunShellModal.showBottomSheet<T>(
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
            color: isDark ? DiaryColors.darkSurface : DiaryColors.background,
            borderRadius: const BorderRadius.vertical(
              top: Radius.circular(NeptunRadius.xl),
            ),
            border: Border(
              top: BorderSide(
                color: cs.outlineVariant.withValues(alpha: 0.35),
              ),
            ),
            boxShadow: [
              BoxShadow(
                color: Colors.black.withValues(alpha: isDark ? 0.45 : 0.12),
                blurRadius: 24,
                offset: const Offset(0, -6),
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
                            style: GoogleFonts.plusJakartaSans(
                              fontSize: 17,
                              fontWeight: FontWeight.w700,
                              color: cs.onSurface,
                              letterSpacing: -0.2,
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
                  physics: const BouncingScrollPhysics(
                    parent: AlwaysScrollableScrollPhysics(),
                  ),
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
