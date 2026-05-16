import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:neptun_alarm_app/core/widgets/neptun_overlay_insets.dart';
import 'package:neptun_alarm_app/features/chat/presentation/providers/chat_controller.dart';

class ChatAgeGateView extends ConsumerStatefulWidget {
  final Widget background;
  const ChatAgeGateView({super.key, required this.background});

  @override
  ConsumerState<ChatAgeGateView> createState() => _ChatAgeGateViewState();
}

class _ChatAgeGateViewState extends ConsumerState<ChatAgeGateView> {
  int? _selectedYear;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final currentYear = DateTime.now().year;
    final birthYears = List.generate(
      100,
      (i) => currentYear - 100 + i,
    ).reversed.toList();

    final bottomChrome = neptunContentBottomPadding(context);

    return Scaffold(
      body: Stack(
        children: [
          widget.background,
          SafeArea(
            bottom: false,
            child: Center(
              child: SingleChildScrollView(
                padding: EdgeInsets.fromLTRB(24, 24, 24, 24 + bottomChrome),
                child: Card(
                  elevation: 0,
                  color: cs.surfaceContainerHigh,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(24),
                    side: BorderSide(color: cs.outlineVariant),
                  ),
                  child: Padding(
                    padding: const EdgeInsets.all(32),
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        CircleAvatar(
                          radius: 36,
                          backgroundColor: cs.primaryContainer,
                          child: Icon(
                            Icons.cake_rounded,
                            size: 40,
                            color: cs.onPrimaryContainer,
                          ),
                        ),
                        const SizedBox(height: 24),
                        Text(
                          'Потрібна перевірка віку',
                          textAlign: TextAlign.center,
                          style: GoogleFonts.plusJakartaSans(
                            fontSize: 22,
                            fontWeight: FontWeight.w800,
                            color: cs.onSurface,
                          ),
                        ),
                        const SizedBox(height: 12),
                        Text(
                          'Для безпеки спільноти чат доступний лише користувачам від 16 років.',
                          textAlign: TextAlign.center,
                          style: GoogleFonts.plusJakartaSans(
                            color: cs.onSurfaceVariant,
                            fontSize: 14,
                            height: 1.45,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                        const SizedBox(height: 32),
                        Material(
                          color: cs.surfaceContainerLow,
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(16),
                            side: BorderSide(color: cs.outlineVariant),
                          ),
                          child: Padding(
                            padding: const EdgeInsets.symmetric(horizontal: 16),
                            child: DropdownButtonHideUnderline(
                              child: DropdownButton<int>(
                                value: _selectedYear,
                                isExpanded: true,
                                hint: Text(
                                  'Ваш рік народження',
                                  style: GoogleFonts.plusJakartaSans(
                                    color: cs.onSurfaceVariant,
                                    fontWeight: FontWeight.w500,
                                  ),
                                ),
                                items: birthYears
                                    .map(
                                      (y) => DropdownMenuItem(
                                        value: y,
                                        child: Text(
                                          '$y',
                                          style: GoogleFonts.plusJakartaSans(
                                            fontWeight: FontWeight.w600,
                                          ),
                                        ),
                                      ),
                                    )
                                    .toList(),
                                onChanged: (v) =>
                                    setState(() => _selectedYear = v),
                              ),
                            ),
                          ),
                        ),
                        const SizedBox(height: 24),
                        FilledButton(
                          onPressed: _selectedYear == null
                              ? null
                              : () {
                                  ref
                                      .read(chatControllerProvider.notifier)
                                      .confirmAge(_selectedYear!);
                                },
                          style: FilledButton.styleFrom(
                            minimumSize: const Size.fromHeight(54),
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(20),
                            ),
                          ),
                          child: Text(
                            'Продовжити',
                            style: GoogleFonts.plusJakartaSans(
                              fontWeight: FontWeight.w800,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class ChatRegistrationView extends ConsumerStatefulWidget {
  final Widget background;
  const ChatRegistrationView({super.key, required this.background});

  @override
  ConsumerState<ChatRegistrationView> createState() =>
      _ChatRegistrationViewState();
}

class _ChatRegistrationViewState extends ConsumerState<ChatRegistrationView> {
  final _nickController = TextEditingController();
  bool _loading = false;

  @override
  void dispose() {
    _nickController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final bottomChrome = neptunContentBottomPadding(context);

    return Scaffold(
      body: Stack(
        children: [
          widget.background,
          SafeArea(
            bottom: false,
            child: Center(
              child: SingleChildScrollView(
                padding: EdgeInsets.fromLTRB(32, 32, 32, 32 + bottomChrome),
                child: Card(
                  elevation: 0,
                  color: cs.surfaceContainerHigh,
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(24),
                    side: BorderSide(color: cs.outlineVariant),
                  ),
                  child: Padding(
                    padding: const EdgeInsets.all(32),
                    child: Column(
                      children: [
                        CircleAvatar(
                          radius: 32,
                          backgroundColor: cs.primaryContainer,
                          child: Icon(
                            Icons.flash_on_rounded,
                            size: 36,
                            color: cs.onPrimaryContainer,
                          ),
                        ),
                        const SizedBox(height: 24),
                        Text(
                          'Привіт!',
                          style: GoogleFonts.plusJakartaSans(
                            fontSize: 28,
                            fontWeight: FontWeight.w900,
                            color: cs.onSurface,
                          ),
                        ),
                        const SizedBox(height: 8),
                        Text(
                          'Оберіть нікнейм для входу в чат',
                          style: GoogleFonts.plusJakartaSans(
                            color: cs.onSurfaceVariant,
                            fontSize: 16,
                            height: 1.4,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                        const SizedBox(height: 32),
                        TextField(
                          controller: _nickController,
                          maxLength: 16,
                          style: GoogleFonts.plusJakartaSans(
                            color: cs.onSurface,
                            fontSize: 18,
                            fontWeight: FontWeight.w700,
                          ),
                          decoration: InputDecoration(
                            hintText: 'Ваш нік у чаті',
                            filled: true,
                            fillColor: cs.surfaceContainerLow,
                            border: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(18),
                              borderSide: BorderSide(color: cs.outlineVariant),
                            ),
                            enabledBorder: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(18),
                              borderSide: BorderSide(color: cs.outlineVariant),
                            ),
                            focusedBorder: OutlineInputBorder(
                              borderRadius: BorderRadius.circular(18),
                              borderSide: BorderSide(
                                color: cs.primary,
                                width: 2,
                              ),
                            ),
                            hintStyle: GoogleFonts.plusJakartaSans(
                              color: cs.onSurfaceVariant.withValues(
                                alpha: 0.65,
                              ),
                              fontSize: 16,
                              fontWeight: FontWeight.w500,
                            ),
                            contentPadding: const EdgeInsets.symmetric(
                              horizontal: 20,
                              vertical: 18,
                            ),
                          ),
                        ),
                        const SizedBox(height: 24),
                        FilledButton(
                          onPressed: _loading
                              ? null
                              : () async {
                                  if (_nickController.text.trim().isEmpty) {
                                    return;
                                  }
                                  setState(() => _loading = true);
                                  await ref
                                      .read(chatControllerProvider.notifier)
                                      .registerNickname(
                                        _nickController.text.trim(),
                                      );
                                  if (mounted) {
                                    setState(() => _loading = false);
                                  }
                                },
                          style: FilledButton.styleFrom(
                            minimumSize: const Size.fromHeight(56),
                            shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(20),
                            ),
                          ),
                          child: _loading
                              ? SizedBox(
                                  height: 24,
                                  width: 24,
                                  child: CircularProgressIndicator(
                                    strokeWidth: 2.5,
                                    color: cs.onPrimary,
                                  ),
                                )
                              : Text(
                                  'Почати спілкування',
                                  style: GoogleFonts.plusJakartaSans(
                                    fontWeight: FontWeight.w700,
                                    fontSize: 16,
                                  ),
                                ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
