import 'dart:ui' show ImageFilter;

import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:firebase_messaging/firebase_messaging.dart';

import '../config/prefs_keys.dart';
import '../core/widgets/neptun_button.dart';
import '../services/notification_service.dart';
import '../core/utils/app_debug_log.dart';
import '../design/neptun_design.dart';
import '../theme/diary_design.dart';
import '../widgets/neptun_card.dart';
import '../features/regions/presentation/regions_selection_provider.dart';

class OnboardingPage extends StatefulWidget {
  const OnboardingPage({super.key});

  @override
  State<OnboardingPage> createState() => _OnboardingPageState();
}

class _OnboardingPageState extends State<OnboardingPage>
    with TickerProviderStateMixin {
  int _currentPage = 0;
  bool _notificationsGranted = false;
  Set<String> _selectedRegions = {};
  bool _isFinishing = false;

  late AnimationController _atmosphere;

  static const _totalPages = 4;

  static const _regions = [
    'Вінницька',
    'Волинська',
    'Дніпропетровська',
    'Донецька',
    'Житомирська',
    'Закарпатська',
    'Запорізька',
    'Івано-Франківська',
    'Київська',
    'Кіровоградська',
    'Луганська',
    'Львівська',
    'Миколаївська',
    'Одеська',
    'Полтавська',
    'Рівненська',
    'Сумська',
    'Тернопільська',
    'Харківська',
    'Херсонська',
    'Хмельницька',
    'Черкаська',
    'Чернівецька',
    'Чернігівська',
    'м. Київ',
  ];

  @override
  void initState() {
    super.initState();
    _atmosphere = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 5200),
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _atmosphere.dispose();
    super.dispose();
  }

  void _goToPage(int page) {
    if (page == _currentPage) return;
    HapticFeedback.lightImpact();
    setState(() => _currentPage = page);
  }

  void _onNext() {
    if (_currentPage < _totalPages - 1) {
      _goToPage(_currentPage + 1);
    } else {
      if (_isFinishing) return;
      _finishOnboarding();
    }
  }

  Future<void> _requestNotifications() async {
    if (kIsWeb) {
      _onNext();
      return;
    }
    try {
      final messaging = FirebaseMessaging.instance;
      final settings = await messaging.requestPermission(
        alert: true,
        badge: true,
        sound: true,
        criticalAlert: true,
      );
      setState(() {
        _notificationsGranted =
            settings.authorizationStatus == AuthorizationStatus.authorized ||
                settings.authorizationStatus ==
                    AuthorizationStatus.provisional;
      });
    } catch (e) {
      appDebugLog('Notification permission error: $e');
    }
    _onNext();
  }

  Future<void> _finishOnboarding() async {
    if (_isFinishing) return;
    setState(() => _isFinishing = true);

    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setBool(PrefsKeys.firstLaunch, false);

      if (_selectedRegions.isNotEmpty) {
        final fullNames = _selectedRegions
            .map((r) => r == 'м. Київ' ? 'м. Київ' : '$r область')
            .toList();
        await prefs.setString('onboarding_region', _selectedRegions.first);
        await prefs.setStringList(PrefsKeys.selectedRegions, fullNames);
        try {
          await NotificationService()
              .updateRegions(fullNames)
              .timeout(const Duration(seconds: 5));
        } catch (e) {
          appDebugLog('Onboarding: updateRegions failed: $e');
        }
      }

      if (!mounted) return;
      ProviderScope.containerOf(context, listen: false)
          .invalidate(regionsSelectionProvider);
      if (!mounted) return;
      context.go('/');
    } catch (e) {
      appDebugLog('Onboarding: save failed: $e');
      if (mounted) context.go('/');
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final cs = Theme.of(context).colorScheme;

    return Scaffold(
      body: Stack(
        fit: StackFit.expand,
        children: [
          _OnboardingAtmosphere(
            animation: _atmosphere,
            pageIndex: _currentPage,
            isDark: isDark,
            cs: cs,
          ),
          AnnotatedRegion<SystemUiOverlayStyle>(
            value: SystemUiOverlayStyle(
              statusBarColor: Colors.transparent,
              statusBarIconBrightness:
                  isDark ? Brightness.light : Brightness.dark,
            ),
            child: SafeArea(
              bottom: false,
              child: Column(
                children: [
                  Padding(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 20, vertical: 6),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.end,
                      children: [
                        if (_currentPage < _totalPages - 1)
                          ClipRRect(
                            borderRadius: BorderRadius.circular(20),
                            child: BackdropFilter(
                              filter: ImageFilter.blur(sigmaX: 12, sigmaY: 12),
                              child: Material(
                                color: cs.surface.withValues(alpha: 0.45),
                                child: InkWell(
                                  onTap: () {
                                    HapticFeedback.selectionClick();
                                    _finishOnboarding();
                                  },
                                  borderRadius: BorderRadius.circular(20),
                                  child: Padding(
                                    padding: const EdgeInsets.symmetric(
                                      horizontal: 16,
                                      vertical: 10,
                                    ),
                                    child: Text(
                                      'Пропустити',
                                      style: GoogleFonts.plusJakartaSans(
                                        fontSize: 14,
                                        fontWeight: FontWeight.w700,
                                        color: cs.onSurface
                                            .withValues(alpha: 0.65),
                                      ),
                                    ),
                                  ),
                                ),
                              ),
                            ),
                          ),
                      ],
                    ),
                  ),
                  Expanded(
                    child: AnimatedSwitcher(
                      duration: const Duration(milliseconds: 560),
                      switchInCurve: Curves.easeOutCubic,
                      switchOutCurve: Curves.easeInCubic,
                      layoutBuilder: (current, previous) {
                        return Stack(
                          alignment: Alignment.center,
                          children: [
                            ...previous,
                            ?current,
                          ],
                        );
                      },
                      transitionBuilder: (child, animation) {
                        final slide = Tween<Offset>(
                          begin: const Offset(0, 0.05),
                          end: Offset.zero,
                        ).animate(CurvedAnimation(
                          parent: animation,
                          curve: Curves.easeOutCubic,
                        ));
                        return FadeTransition(
                          opacity: animation,
                          child: SlideTransition(
                            position: slide,
                            child: child,
                          ),
                        );
                      },
                      child: KeyedSubtree(
                        key: ValueKey<int>(_currentPage),
                        child: _buildPage(_currentPage, cs, isDark),
                      ),
                    ),
                  ),
                  Padding(
                    padding: const EdgeInsets.fromLTRB(
                      NeptunSpacing.screenHorizontal,
                      NeptunSpacing.lg,
                      NeptunSpacing.screenHorizontal,
                      NeptunSpacing.xxxl,
                    ),
                    child: Row(
                      children: [
                        Row(
                          children: List.generate(
                            _totalPages,
                            (i) => Padding(
                              padding: const EdgeInsets.only(right: 8),
                              child: AnimatedScale(
                                scale: _currentPage == i ? 1.0 : 0.92,
                                duration: const Duration(milliseconds: 320),
                                curve: Curves.easeOutBack,
                                child: AnimatedContainer(
                                  duration:
                                      const Duration(milliseconds: 380),
                                  curve: Curves.easeOutCubic,
                                  height: 7,
                                  width: _currentPage == i ? 32 : 7,
                                  decoration: BoxDecoration(
                                    borderRadius: BorderRadius.circular(4),
                                    gradient: _currentPage == i
                                        ? LinearGradient(
                                            colors: [
                                              cs.primary,
                                              cs.primary
                                                  .withValues(alpha: 0.65),
                                            ],
                                          )
                                        : null,
                                    color: _currentPage == i
                                        ? null
                                        : cs.onSurface
                                            .withValues(alpha: 0.12),
                                    boxShadow: _currentPage == i
                                        ? [
                                            BoxShadow(
                                              color: cs.primary.withValues(
                                                alpha: 0.35,
                                              ),
                                              blurRadius: 10,
                                              offset: const Offset(0, 2),
                                            ),
                                          ]
                                        : null,
                                  ),
                                ),
                              ),
                            ),
                          ),
                        ),
                        const Spacer(),
                        if (_currentPage == 0 ||
                            _currentPage == _totalPages - 1)
                          NeptunButton(
                            label: _currentPage == _totalPages - 1
                                ? 'Почати'
                                : 'Далі',
                            onPressed:
                                _isFinishing ? null : _onNext,
                            isLoading: _currentPage == _totalPages - 1 &&
                                _isFinishing,
                          ),
                      ],
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

  Widget _buildPage(int page, ColorScheme cs, bool isDark) {
    switch (page) {
      case 0:
        return _buildWelcomePage(cs, isDark);
      case 1:
        return _buildRegionPage(cs, isDark);
      case 2:
        return _buildNotificationPage(cs, isDark);
      case 3:
        return _buildReadyPage(cs, isDark);
      default:
        return const SizedBox.shrink();
    }
  }

  Widget _buildWelcomePage(ColorScheme cs, bool isDark) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: NeptunSpacing.xxl),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          _HeroGlowIcon(
            icon: Icons.shield_rounded,
            primary: cs.primary,
            onPrimary: cs.onPrimary,
            isDark: isDark,
            size: 116,
          ),
          const SizedBox(height: NeptunSpacing.xxxl),
          Text(
            'Ваша безпека —\nнаш пріоритет',
            textAlign: TextAlign.center,
            style: GoogleFonts.plusJakartaSans(
              fontSize: NeptunTypography.hero + 2,
              fontWeight: FontWeight.w800,
              color: cs.onSurface,
              height: 1.08,
              letterSpacing: -1.1,
            ),
          ),
          const SizedBox(height: NeptunSpacing.lg),
          Text(
            'Миттєві сповіщення про загрози, карта в реальному часі '
            'та перевірена спільнота.',
            textAlign: TextAlign.center,
            style: GoogleFonts.plusJakartaSans(
              fontSize: NeptunTypography.body,
              color: cs.onSurface.withValues(alpha: 0.55),
              height: 1.55,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildRegionPage(ColorScheme cs, bool isDark) {
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: NeptunSpacing.xl),
          child: Column(
            children: [
              _HeroGlowIcon(
                icon: Icons.location_on_rounded,
                primary: cs.primary,
                onPrimary: cs.onPrimary,
                isDark: isDark,
                size: 88,
                softTint: cs.primary.withValues(alpha: 0.2),
              ),
              const SizedBox(height: NeptunSpacing.lg),
              Text(
                'Оберіть регіони',
                style: GoogleFonts.plusJakartaSans(
                  fontSize: NeptunTypography.h2 + 2,
                  fontWeight: FontWeight.w800,
                  color: cs.onSurface,
                  letterSpacing: -0.3,
                ),
              ),
              const SizedBox(height: 6),
              Text(
                'Миттєві сповіщення для обраних зон',
                textAlign: TextAlign.center,
                style: GoogleFonts.plusJakartaSans(
                  fontSize: NeptunTypography.caption,
                  color: cs.onSurface.withValues(alpha: 0.5),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: NeptunSpacing.xl),
        Expanded(
          child: ListView.builder(
            padding: const EdgeInsets.symmetric(
              horizontal: NeptunSpacing.screenHorizontal,
            ),
            itemCount: _regions.length + 1,
            itemBuilder: (context, index) {
              if (index == 0) {
                final allSelected =
                    _selectedRegions.length == _regions.length;
                return Padding(
                  padding: const EdgeInsets.only(bottom: NeptunSpacing.md),
                  child: NeptunCard(
                    padding: EdgeInsets.zero,
                    borderRadius: NeptunRadius.md,
                    backgroundColor: allSelected
                        ? cs.primary.withValues(alpha: 0.12)
                        : null,
                    borderColor: allSelected
                        ? cs.primary.withValues(alpha: 0.45)
                        : null,
                    onTap: () {
                      HapticFeedback.selectionClick();
                      setState(() {
                        if (allSelected) {
                          _selectedRegions.clear();
                        } else {
                          _selectedRegions = _regions.toSet();
                        }
                      });
                    },
                    child: Padding(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 16,
                        vertical: 14,
                      ),
                      child: Row(
                        children: [
                          Icon(
                            Icons.checklist_rounded,
                            size: 22,
                            color: allSelected
                                ? cs.primary
                                : cs.onSurface.withValues(alpha: 0.35),
                          ),
                          const SizedBox(width: 12),
                          Text(
                            'Всі регіони',
                            style: GoogleFonts.plusJakartaSans(
                              fontSize: NeptunTypography.body,
                              fontWeight: allSelected
                                  ? FontWeight.w700
                                  : FontWeight.w500,
                              color: cs.onSurface,
                            ),
                          ),
                          const Spacer(),
                          if (allSelected)
                            Icon(
                              Icons.check_circle_rounded,
                              size: 22,
                              color: cs.primary,
                            ),
                        ],
                      ),
                    ),
                  ),
                );
              }
              final region = _regions[index - 1];
              final isSelected = _selectedRegions.contains(region);
              return TweenAnimationBuilder<double>(
                tween: Tween(begin: 0, end: 1),
                duration: Duration(milliseconds: 280 + (index * 12).clamp(0, 200)),
                curve: Curves.easeOutCubic,
                builder: (context, t, child) {
                  return Opacity(
                    opacity: t,
                    child: Transform.translate(
                      offset: Offset(0, 8 * (1 - t)),
                      child: child,
                    ),
                  );
                },
                child: Padding(
                  padding: const EdgeInsets.only(bottom: NeptunSpacing.sm),
                  child: NeptunCard(
                    padding: EdgeInsets.zero,
                    borderRadius: NeptunRadius.md,
                    backgroundColor: isSelected
                        ? cs.primary.withValues(alpha: 0.06)
                        : null,
                    borderColor: isSelected
                        ? cs.primary.withValues(alpha: 0.35)
                        : null,
                    onTap: () {
                      HapticFeedback.selectionClick();
                      setState(() {
                        if (isSelected) {
                          _selectedRegions.remove(region);
                        } else {
                          _selectedRegions.add(region);
                        }
                      });
                    },
                    child: Padding(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 16,
                        vertical: 14,
                      ),
                      child: Row(
                        children: [
                          Text(
                            region,
                            style: GoogleFonts.plusJakartaSans(
                              fontSize: NeptunTypography.body,
                              fontWeight: isSelected
                                  ? FontWeight.w700
                                  : FontWeight.w400,
                              color: cs.onSurface,
                            ),
                          ),
                          const Spacer(),
                          if (isSelected)
                            Icon(
                              Icons.check_circle_rounded,
                              size: 22,
                              color: cs.primary,
                            ),
                        ],
                      ),
                    ),
                  ),
                ),
              );
            },
          ),
        ),
        Padding(
          padding: const EdgeInsets.all(NeptunSpacing.xl),
          child: NeptunButton(
            label: _selectedRegions.isEmpty
                ? 'Пропустити'
                : 'Далі${_selectedRegions.length > 1 ? ' (${_selectedRegions.length})' : ''}',
            isExpanded: true,
            onPressed: _onNext,
          ),
        ),
      ],
    );
  }

  Widget _buildNotificationPage(ColorScheme cs, bool isDark) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: NeptunSpacing.xxl),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          _HeroGlowIcon(
            icon: Icons.notifications_active_rounded,
            primary: NeptunStatus.alarm,
            onPrimary: Colors.white,
            isDark: isDark,
            size: 108,
            softTint: NeptunStatus.alarm.withValues(alpha: 0.22),
          ),
          const SizedBox(height: NeptunSpacing.xxxl),
          Text(
            'Увімкніть\nсповіщення',
            textAlign: TextAlign.center,
            style: GoogleFonts.plusJakartaSans(
              fontSize: NeptunTypography.h1 + 2,
              fontWeight: FontWeight.w800,
              color: cs.onSurface,
              height: 1.1,
              letterSpacing: -0.6,
            ),
          ),
          const SizedBox(height: NeptunSpacing.lg),
          Text(
            'Це критично для вашої безпеки. Сповіщення про загрози '
            'приходять миттєво.',
            textAlign: TextAlign.center,
            style: GoogleFonts.plusJakartaSans(
              fontSize: NeptunTypography.body,
              color: cs.onSurface.withValues(alpha: 0.55),
              height: 1.55,
            ),
          ),
          const SizedBox(height: NeptunSpacing.xxl),
          NeptunButton(
            label: _notificationsGranted
                ? 'Сповіщення увімкнено'
                : 'Увімкнути сповіщення',
            icon: _notificationsGranted
                ? Icons.check_circle_rounded
                : Icons.notifications_rounded,
            isExpanded: true,
            onPressed:
                _notificationsGranted ? _onNext : _requestNotifications,
          ),
          if (!_notificationsGranted) ...[
            const SizedBox(height: NeptunSpacing.md),
            TextButton(
              onPressed: _onNext,
              child: Text(
                'Пізніше',
                style: GoogleFonts.plusJakartaSans(
                  fontSize: NeptunTypography.caption,
                  fontWeight: FontWeight.w700,
                  color: cs.onSurface.withValues(alpha: 0.45),
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildReadyPage(ColorScheme cs, bool isDark) {
    final features = [
      (Icons.map_rounded, 'Карта в реальному часі'),
      (Icons.radar_rounded, 'Радар загроз'),
      (Icons.chat_rounded, 'Модерований чат'),
      (Icons.notifications_rounded, 'Миттєві сповіщення'),
    ];
    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(
        horizontal: NeptunSpacing.xxl,
        vertical: NeptunSpacing.lg,
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          _HeroGlowIcon(
            icon: Icons.rocket_launch_rounded,
            primary: NeptunStatus.safe,
            onPrimary: Colors.white,
            isDark: isDark,
            size: 104,
            softTint: NeptunStatus.safe.withValues(alpha: 0.25),
          ),
          const SizedBox(height: NeptunSpacing.xxxl),
          Text(
            'Все готово!',
            textAlign: TextAlign.center,
            style: GoogleFonts.plusJakartaSans(
              fontSize: NeptunTypography.h1 + 4,
              fontWeight: FontWeight.w800,
              color: cs.onSurface,
              height: 1.08,
              letterSpacing: -0.5,
            ),
          ),
          const SizedBox(height: NeptunSpacing.lg),
          Text(
            'Карта, радар загроз, модерований чат — '
            'все для вашої безпеки.',
            textAlign: TextAlign.center,
            style: GoogleFonts.plusJakartaSans(
              fontSize: NeptunTypography.body,
              color: cs.onSurface.withValues(alpha: 0.55),
              height: 1.55,
            ),
          ),
          const SizedBox(height: NeptunSpacing.xxl),
          ...List.generate(features.length, (i) {
            final item = features[i];
            return TweenAnimationBuilder<double>(
              tween: Tween(begin: 0, end: 1),
              duration: Duration(milliseconds: 400 + i * 90),
              curve: Curves.easeOutCubic,
              builder: (context, t, _) {
                return Opacity(
                  opacity: t,
                  child: Transform.translate(
                    offset: Offset(16 * (1 - t), 0),
                    child: Padding(
                      padding:
                          const EdgeInsets.only(bottom: NeptunSpacing.md),
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 16,
                          vertical: 14,
                        ),
                        decoration: BoxDecoration(
                          borderRadius: BorderRadius.circular(16),
                          color: cs.surfaceContainerHighest
                              .withValues(alpha: 0.55),
                          border: Border.all(
                            color: cs.outlineVariant.withValues(alpha: 0.35),
                          ),
                        ),
                        child: Row(
                          children: [
                            Container(
                              padding: const EdgeInsets.all(10),
                              decoration: BoxDecoration(
                                color: cs.primary.withValues(alpha: 0.12),
                                borderRadius: BorderRadius.circular(12),
                              ),
                              child: Icon(
                                item.$1,
                                size: 22,
                                color: cs.primary,
                              ),
                            ),
                            const SizedBox(width: 14),
                            Expanded(
                              child: Text(
                                item.$2,
                                style: GoogleFonts.plusJakartaSans(
                                  fontSize: NeptunTypography.body,
                                  fontWeight: FontWeight.w600,
                                  color: cs.onSurface.withValues(alpha: 0.88),
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                );
              },
            );
          }),
        ],
      ),
    );
  }
}

class _OnboardingAtmosphere extends StatelessWidget {
  const _OnboardingAtmosphere({
    required this.animation,
    required this.pageIndex,
    required this.isDark,
    required this.cs,
  });

  final Animation<double> animation;
  final int pageIndex;
  final bool isDark;
  final ColorScheme cs;

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: animation,
      builder: (context, _) {
        final t = animation.value;
        final drift = (t - 0.5) * 0.08;
        final base = isDark ? DiaryColors.darkBackground : DiaryColors.background;
        final accents = [
          [cs.primary.withValues(alpha: 0.14), cs.tertiary.withValues(alpha: 0.08)],
          [cs.primary.withValues(alpha: 0.18), cs.secondary.withValues(alpha: 0.1)],
          [NeptunStatus.alarm.withValues(alpha: 0.12), cs.primary.withValues(alpha: 0.06)],
          [NeptunStatus.safe.withValues(alpha: 0.14), DiaryColors.premiumGold.withValues(alpha: 0.08)],
        ];
        final pair = accents[pageIndex.clamp(0, accents.length - 1)];
        return DecoratedBox(
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment(-0.9 + drift, -1),
              end: Alignment(0.85 - drift, 1.1),
              colors: [
                Color.lerp(pair[0], pair[1], t)!,
                base,
                Color.lerp(pair[1], pair[0], t * 0.5)!,
              ],
              stops: const [0.0, 0.55, 1.0],
            ),
          ),
          child: Stack(
            fit: StackFit.expand,
            children: [
              Positioned(
                top: -80 + t * 40,
                right: -60,
                child: _blurOrb(
                  color: pair[0].withValues(alpha: 0.45),
                  size: 240,
                ),
              ),
              Positioned(
                bottom: -40 - t * 30,
                left: -50,
                child: _blurOrb(
                  color: pair[1].withValues(alpha: 0.4),
                  size: 200,
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _blurOrb({required Color color, required double size}) {
    return IgnorePointer(
      child: Container(
        width: size,
        height: size,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          color: color,
        ),
      ),
    );
  }
}

class _HeroGlowIcon extends StatefulWidget {
  const _HeroGlowIcon({
    required this.icon,
    required this.primary,
    required this.onPrimary,
    required this.isDark,
    required this.size,
    this.softTint,
  });

  final IconData icon;
  final Color primary;
  final Color onPrimary;
  final bool isDark;
  final double size;
  final Color? softTint;

  @override
  State<_HeroGlowIcon> createState() => _HeroGlowIconState();
}

class _HeroGlowIconState extends State<_HeroGlowIcon>
    with SingleTickerProviderStateMixin {
  late AnimationController _c;

  @override
  void initState() {
    super.initState();
    _c = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 2800),
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final glow = widget.softTint ?? widget.primary.withValues(alpha: 0.18);
    return AnimatedBuilder(
      animation: _c,
      builder: (context, _) {
        final p = 0.5 + 0.5 * _c.value;
        return SizedBox(
          width: widget.size + 48,
          height: widget.size + 48,
          child: Stack(
            alignment: Alignment.center,
            children: [
              Container(
                width: widget.size + 28 * p,
                height: widget.size + 28 * p,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  boxShadow: [
                    BoxShadow(
                      color: glow.withValues(alpha: 0.55 + 0.2 * p),
                      blurRadius: 36 + 16 * p,
                      spreadRadius: 2,
                    ),
                  ],
                ),
              ),
              Container(
                width: widget.size,
                height: widget.size,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(widget.size * 0.29),
                  gradient: LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: [
                      widget.primary,
                      widget.primary.withValues(alpha: 0.88),
                    ],
                  ),
                  boxShadow: [
                    BoxShadow(
                      color: widget.primary.withValues(alpha: 0.35),
                      blurRadius: 20,
                      offset: const Offset(0, 12),
                    ),
                  ],
                ),
                child: Stack(
                  alignment: Alignment.center,
                  children: [
                    Positioned.fill(
                      child: DecoratedBox(
                        decoration: BoxDecoration(
                          borderRadius:
                              BorderRadius.circular(widget.size * 0.29),
                          border: Border.all(
                            color: Colors.white.withValues(
                              alpha: widget.isDark ? 0.16 : 0.28,
                            ),
                            width: 1.2,
                          ),
                        ),
                      ),
                    ),
                    Icon(
                      widget.icon,
                      size: widget.size * 0.46,
                      color: widget.onPrimary,
                    ),
                  ],
                ),
              ),
            ],
          ),
        );
      },
    );
  }
}
