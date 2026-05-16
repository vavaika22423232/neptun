import 'dart:ui' show ImageFilter;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';

import '../core/providers/providers.dart';

/// Показує банер: «Немає зʼєднання» або «Сервер недоступний».
class OfflineBanner extends ConsumerWidget {
  const OfflineBanner({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final state = ref.watch(effectiveOnlineProvider);

    return AnimatedSwitcher(
      duration: const Duration(milliseconds: 320),
      switchInCurve: Curves.easeOutCubic,
      switchOutCurve: Curves.easeInCubic,
      child: state.when(
        data: (s) => s == EffectiveOnlineState.online
            ? const SizedBox.shrink()
            : _BannerContent(
                key: ValueKey(s.toString()),
                isApiDown: s == EffectiveOnlineState.apiUnreachable,
              ),
        loading: () => const SizedBox.shrink(),
        error: (_, _) => const SizedBox.shrink(),
      ),
    );
  }
}

class _BannerContent extends StatelessWidget {
  final bool isApiDown;

  const _BannerContent({super.key, this.isApiDown = false});

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final isDark = Theme.of(context).brightness == Brightness.dark;

    final title = isApiDown ? 'Сервер недоступний' : 'Немає з\'єднання з інтернетом';
    final subtitle = isApiDown
        ? 'Спробуйте пізніше — перевіряємо зв\'язок із сервером'
        : 'Перевірте Wi‑Fi або мобільні дані';

    final accent = cs.error;
    final icon = isApiDown ? Icons.cloud_off_rounded : Icons.wifi_off_rounded;

    return Semantics(
      container: true,
      liveRegion: true,
      label: title,
      child: ClipRRect(
        child: BackdropFilter(
          filter: ImageFilter.blur(sigmaX: 12, sigmaY: 12),
          child: DecoratedBox(
            decoration: BoxDecoration(
              border: Border(
                bottom: BorderSide(
                  color: accent.withValues(alpha: isDark ? 0.35 : 0.28),
                  width: 0.8,
                ),
              ),
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: [
                  accent.withValues(alpha: isDark ? 0.22 : 0.14),
                  cs.surface.withValues(alpha: isDark ? 0.72 : 0.88),
                ],
              ),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withValues(alpha: isDark ? 0.25 : 0.06),
                  blurRadius: 12,
                  offset: const Offset(0, 4),
                ),
              ],
            ),
            child: SafeArea(
              top: false,
              child: Padding(
                padding: const EdgeInsets.fromLTRB(16, 12, 16, 12),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    DecoratedBox(
                      decoration: BoxDecoration(
                        color: accent.withValues(alpha: 0.18),
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(
                          color: accent.withValues(alpha: 0.35),
                        ),
                      ),
                      child: Padding(
                        padding: const EdgeInsets.all(10),
                        child: Icon(icon, size: 22, color: accent),
                      ),
                    ),
                    const SizedBox(width: 14),
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Text(
                            title,
                            style: GoogleFonts.plusJakartaSans(
                              fontSize: 14,
                              fontWeight: FontWeight.w700,
                              height: 1.2,
                              letterSpacing: 0.15,
                              color: accent.withValues(alpha: 0.95),
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            subtitle,
                            style: GoogleFonts.plusJakartaSans(
                              fontSize: 12,
                              fontWeight: FontWeight.w500,
                              height: 1.35,
                              color: cs.onSurface.withValues(
                                alpha: isDark ? 0.65 : 0.58,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
