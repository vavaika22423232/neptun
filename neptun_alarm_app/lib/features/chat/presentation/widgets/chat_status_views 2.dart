import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../../../core/widgets/neptun_overlay_insets.dart';

class ChatLoadingView extends StatelessWidget {
  const ChatLoadingView({super.key});

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Scaffold(
      backgroundColor: cs.surface,
      body: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            SizedBox(
              width: 36,
              height: 36,
              child: CircularProgressIndicator(
                strokeWidth: 3,
                color: cs.primary,
              ),
            ),
            const SizedBox(height: 20),
            Text(
              'Завантаження чату…',
              style: GoogleFonts.plusJakartaSans(
                fontSize: 15,
                fontWeight: FontWeight.w600,
                color: cs.onSurfaceVariant,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class ChatRulesView extends StatelessWidget {
  final VoidCallback onAgree;
  final Widget background;

  const ChatRulesView({
    super.key,
    required this.onAgree,
    required this.background,
  });

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final bottomChrome = neptunContentBottomPadding(context);

    return Scaffold(
      body: Stack(
        children: [
          background,
          ColoredBox(color: cs.scrim.withValues(alpha: 0.56)),
          SafeArea(
            bottom: false,
            child: SingleChildScrollView(
              padding: EdgeInsets.fromLTRB(24, 24, 24, 24 + bottomChrome),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const SizedBox(height: 16),
                  Center(
                    child: CircleAvatar(
                      radius: 44,
                      backgroundColor: cs.primaryContainer,
                      child: Icon(
                        Icons.gavel_rounded,
                        size: 40,
                        color: cs.onPrimaryContainer,
                      ),
                    ),
                  ),
                  const SizedBox(height: 24),
                  Center(
                    child: Text(
                      'Правила спільноти',
                      textAlign: TextAlign.center,
                      style: GoogleFonts.plusJakartaSans(
                        fontSize: 28,
                        fontWeight: FontWeight.w900,
                        letterSpacing: -0.5,
                        color: cs.onSurface,
                      ),
                    ),
                  ),
                  const SizedBox(height: 28),
                  _buildRule(
                    context,
                    'Будьте ввічливими',
                    'Поважайте інших учасників чату та їх думку.',
                  ),
                  _buildRule(
                    context,
                    'Без спаму',
                    'Не надсилайте однакові повідомлення або беззмістовний текст.',
                  ),
                  _buildRule(
                    context,
                    'Без мату',
                    'Ми підтримуємо культурне спілкування без нецензурної лексики.',
                  ),
                  _buildRule(
                    context,
                    'Без реклами',
                    'Реклама сторонніх ресурсів або послуг суворо заборонена.',
                  ),
                  const SizedBox(height: 28),
                  Semantics(
                    button: true,
                    label: 'Погодитися з правилами спільноти',
                    child: FilledButton(
                      onPressed: onAgree,
                      style: FilledButton.styleFrom(
                        minimumSize: const Size.fromHeight(56),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(20),
                        ),
                      ),
                      child: Text(
                        'Я згоден з правилами',
                        style: GoogleFonts.plusJakartaSans(
                          fontWeight: FontWeight.w800,
                          fontSize: 17,
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildRule(BuildContext context, String title, String desc) {
    final cs = Theme.of(context).colorScheme;

    return Card(
      elevation: 0,
      margin: const EdgeInsets.only(bottom: 16),
      color: cs.surfaceContainerHigh,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(20),
        side: BorderSide(color: cs.outlineVariant),
      ),
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title,
              style: GoogleFonts.plusJakartaSans(
                fontWeight: FontWeight.w800,
                fontSize: 16,
                color: cs.onSurface,
              ),
            ),
            const SizedBox(height: 6),
            Text(
              desc,
              style: GoogleFonts.plusJakartaSans(
                color: cs.onSurfaceVariant,
                fontSize: 14,
                height: 1.45,
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class ChatBannedView extends StatelessWidget {
  final String? reason;
  final VoidCallback onCheck;

  const ChatBannedView({super.key, this.reason, required this.onCheck});

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;

    return Scaffold(
      backgroundColor: cs.surface,
      body: SafeArea(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            CircleAvatar(
              radius: 52,
              backgroundColor: cs.errorContainer,
              child: Icon(
                Icons.block_rounded,
                size: 56,
                color: cs.onErrorContainer,
              ),
            ),
            const SizedBox(height: 32),
            Text(
              'Доступ обмежено',
              style: GoogleFonts.plusJakartaSans(
                fontSize: 28,
                fontWeight: FontWeight.w900,
                color: cs.error,
              ),
            ),
            const SizedBox(height: 16),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 40),
              child: Text(
                reason ??
                    'Ваш акаунт було заблоковано за порушення правил спільноти.',
                textAlign: TextAlign.center,
                style: GoogleFonts.plusJakartaSans(
                  fontSize: 16,
                  color: cs.onSurfaceVariant,
                  height: 1.5,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ),
            const SizedBox(height: 48),
            FilledButton(
              onPressed: onCheck,
              style: FilledButton.styleFrom(
                backgroundColor: cs.error,
                foregroundColor: cs.onError,
                padding: const EdgeInsets.symmetric(
                  horizontal: 32,
                  vertical: 16,
                ),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(20),
                ),
              ),
              child: Text(
                'Перевірити знову',
                style: GoogleFonts.plusJakartaSans(
                  fontWeight: FontWeight.w700,
                  fontSize: 16,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
