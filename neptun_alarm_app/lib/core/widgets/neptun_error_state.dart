import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';
import 'neptun_button.dart';

/// Consistent error state widget with retry capability.
class NeptunErrorState extends StatelessWidget {
  final String message;
  final String? detail;
  final VoidCallback? onRetry;
  final IconData icon;

  const NeptunErrorState({
    super.key,
    this.message = 'Щось пішло не так',
    this.detail,
    this.onRetry,
    this.icon = Icons.error_outline_rounded,
  });

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;

    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 72,
              height: 72,
              decoration: BoxDecoration(
                color: cs.error.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(20),
              ),
              child: Icon(
                icon,
                size: 32,
                color: cs.error.withValues(alpha: 0.6),
              ),
            ),
            const SizedBox(height: 20),
            Text(
              message,
              style: GoogleFonts.plusJakartaSans(
                fontSize: 17,
                fontWeight: FontWeight.w600,
                color: cs.onSurface,
              ),
              textAlign: TextAlign.center,
            ),
            if (detail != null) ...[
              const SizedBox(height: 8),
              Text(
                detail!,
                style: GoogleFonts.plusJakartaSans(
                  fontSize: 14,
                  color: cs.onSurface.withValues(alpha: 0.5),
                ),
                textAlign: TextAlign.center,
              ),
            ],
            if (onRetry != null) ...[
              const SizedBox(height: 20),
              NeptunButton.secondary(
                label: 'Спробувати знову',
                icon: Icons.refresh_rounded,
                onPressed: onRetry,
              ),
            ],
          ],
        ),
      ),
    );
  }
}

/// Inline error banner for top-of-page errors (non-blocking).
class NeptunErrorBanner extends StatelessWidget {
  final String message;
  final String? detail;
  final VoidCallback? onRetry;
  final VoidCallback? onDismiss;

  const NeptunErrorBanner({
    super.key,
    required this.message,
    this.detail,
    this.onRetry,
    this.onDismiss,
  });

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;

    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: cs.error.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: cs.error.withValues(alpha: 0.2), width: 0.5),
      ),
      child: Row(
        children: [
          Icon(Icons.warning_amber_rounded, size: 18, color: cs.error),
          const SizedBox(width: 10),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  message,
                  style: GoogleFonts.plusJakartaSans(
                    fontSize: 13,
                    fontWeight: FontWeight.w500,
                    color: cs.error,
                  ),
                ),
                if (detail != null && detail!.isNotEmpty) ...[
                  const SizedBox(height: 6),
                  Text(
                    detail!,
                    style: GoogleFonts.plusJakartaSans(
                      fontSize: 12,
                      fontWeight: FontWeight.w400,
                      height: 1.35,
                      color: cs.onSurface.withValues(alpha: 0.55),
                    ),
                  ),
                ],
              ],
            ),
          ),
          if (onRetry != null)
            IconButton(
              onPressed: () {
                HapticFeedback.mediumImpact();
                onRetry?.call();
              },
              icon: Icon(Icons.refresh_rounded, size: 18, color: cs.error),
              constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
              padding: EdgeInsets.zero,
            ),
          if (onDismiss != null)
            IconButton(
              onPressed: onDismiss,
              icon: Icon(Icons.close_rounded, size: 18, color: cs.error),
              constraints: const BoxConstraints(minWidth: 32, minHeight: 32),
              padding: EdgeInsets.zero,
            ),
        ],
      ),
    );
  }
}
