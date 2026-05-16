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
      duration: const Duration(milliseconds: 300),
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

    return Material(
      color: cs.error.withValues(alpha: 0.12),
      child: SafeArea(
        top: false,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
          child: Row(
            children: [
              Icon(
                isApiDown ? Icons.cloud_off_rounded : Icons.wifi_off_rounded,
                size: 20,
                color: cs.error,
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  isApiDown ? 'Сервер недоступний' : 'Немає з\'єднання з інтернетом',
                  style: GoogleFonts.plusJakartaSans(
                    fontSize: 13,
                    fontWeight: FontWeight.w500,
                    color: cs.error,
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
