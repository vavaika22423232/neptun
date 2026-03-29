import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import '../config/prefs_keys.dart';
import '../core/widgets/neptun_button.dart';
import '../services/notification_service.dart';

class OnboardingPage extends StatefulWidget {
  const OnboardingPage({super.key});

  @override
  State<OnboardingPage> createState() => _OnboardingPageState();
}

class _OnboardingPageState extends State<OnboardingPage> {
  final PageController _pageController = PageController();
  int _currentPage = 0;
  bool _notificationsGranted = false;
  Set<String> _selectedRegions = {};
  bool _isFinishing = false;

  static const _totalPages = 4;

  static const _regions = [
    'Вінницька', 'Волинська', 'Дніпропетровська', 'Донецька',
    'Житомирська', 'Закарпатська', 'Запорізька', 'Івано-Франківська',
    'Київська', 'Кіровоградська', 'Луганська', 'Львівська',
    'Миколаївська', 'Одеська', 'Полтавська', 'Рівненська',
    'Сумська', 'Тернопільська', 'Харківська', 'Херсонська',
    'Хмельницька', 'Черкаська', 'Чернівецька', 'Чернігівська',
    'м. Київ',
  ];

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }

  void _goToPage(int page) {
    _pageController.animateToPage(
      page,
      duration: const Duration(milliseconds: 300),
      curve: Curves.easeInOut,
    );
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
            settings.authorizationStatus == AuthorizationStatus.provisional;
      });
    } catch (e) {
      debugPrint('Notification permission error: $e');
    }
    _onNext();
  }

  Future<void> _finishOnboarding() async {
    if (_isFinishing) return;
    setState(() => _isFinishing = true);

    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setBool(PrefsKeys.firstLaunch, false);

      // Navigate immediately so user sees response; region/notifications in background
      if (!mounted) return;
      context.go('/');

      if (_selectedRegions.isNotEmpty) {
        final fullNames = _selectedRegions.map((r) =>
            r == 'м. Київ' ? 'м. Київ' : '$r область').toList();
        await prefs.setString('onboarding_region',
            _selectedRegions.first); // legacy, first for backwards compat
        await prefs.setStringList('selected_regions', fullNames);
        try {
          await NotificationService()
              .updateRegions(fullNames)
              .timeout(const Duration(seconds: 5));
        } catch (e) {
          debugPrint('Onboarding: updateRegions failed: $e');
        }
      }
    } catch (e) {
      debugPrint('Onboarding: save failed: $e');
      if (mounted) context.go('/');
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final cs = Theme.of(context).colorScheme;

    return Scaffold(
      body: Container(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: isDark
                ? [
                    cs.surface,
                    cs.surfaceContainer.withValues(alpha: 0.4),
                    cs.surface,
                  ]
                : [
                    cs.surface,
                    cs.surfaceContainerHighest.withValues(alpha: 0.5),
                    cs.surface,
                  ],
          ),
        ),
        child: AnnotatedRegion<SystemUiOverlayStyle>(
        value: SystemUiOverlayStyle(
          statusBarColor: Colors.transparent,
          statusBarIconBrightness: isDark ? Brightness.light : Brightness.dark,
        ),
        child: SafeArea(
          bottom: false,
          child: Column(
            children: [
              // Skip button
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 8),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.end,
                  children: [
                    if (_currentPage < _totalPages - 1)
                      TextButton(
                        onPressed: () {
                          HapticFeedback.selectionClick();
                          _finishOnboarding();
                        },
                        child: Text(
                          'Пропустити',
                          style: GoogleFonts.plusJakartaSans(
                            fontSize: 14,
                            fontWeight: FontWeight.w600,
                            color: cs.onSurface.withValues(alpha: 0.5),
                          ),
                        ),
                      ),
                  ],
                ),
              ),

              // Pages
              Expanded(
                child: PageView(
                  controller: _pageController,
                  onPageChanged: (p) => setState(() => _currentPage = p),
                  physics: const NeverScrollableScrollPhysics(),
                  children: [
                    _buildWelcomePage(cs, isDark),
                    _buildRegionPage(cs, isDark),
                    _buildNotificationPage(cs, isDark),
                    _buildReadyPage(cs, isDark),
                  ],
                ),
              ),

              // Bottom controls
              Padding(
                padding: const EdgeInsets.fromLTRB(24, 16, 24, 48),
                child: Row(
                  children: [
                    // Indicators
                    Row(
                      children: List.generate(
                        _totalPages,
                        (i) => AnimatedContainer(
                          duration: const Duration(milliseconds: 300),
                          margin: const EdgeInsets.only(right: 8),
                          height: 6,
                          width: _currentPage == i ? 24 : 6,
                          decoration: BoxDecoration(
                            color: _currentPage == i
                                ? cs.primary
                                : cs.onSurface.withValues(alpha: 0.15),
                            borderRadius: BorderRadius.circular(3),
                          ),
                        ),
                      ),
                    ),
                    const Spacer(),
                    // Next button (pages 0 and 3 only -- pages 1 and 2 have inline buttons)
                    if (_currentPage == 0 || _currentPage == _totalPages - 1)
                      NeptunButton(
                        label: _currentPage == _totalPages - 1 ? 'Почати' : 'Далі',
                        onPressed: _isFinishing ? null : _onNext,
                        isLoading: _currentPage == _totalPages - 1 && _isFinishing,
                      ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    ),
    );
  }

  // Page 1: Welcome
  Widget _buildWelcomePage(ColorScheme cs, bool isDark) {
    return Padding(
      padding: const EdgeInsets.all(40),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Container(
            width: 100,
            height: 100,
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [cs.primary, cs.primary.withValues(alpha: 0.8)],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
              borderRadius: BorderRadius.circular(28),
              boxShadow: [
                BoxShadow(
                  color: cs.primary.withValues(alpha: 0.3),
                  blurRadius: 30,
                  spreadRadius: 5,
                ),
              ],
            ),
            child: const Icon(Icons.shield_rounded, size: 48, color: Colors.white),
          ),
          const SizedBox(height: 48),
          Text(
            'Ваша безпека —\nнаш пріоритет',
            textAlign: TextAlign.center,
            style: GoogleFonts.plusJakartaSans(
              fontSize: 28,
              fontWeight: FontWeight.w800,
              color: cs.onSurface,
              height: 1.2,
              letterSpacing: -0.5,
            ),
          ),
          const SizedBox(height: 16),
          Text(
            'Миттєві сповіщення про загрози, карта в реальному часі '
            'та перевірена спільнота.',
            textAlign: TextAlign.center,
            style: GoogleFonts.plusJakartaSans(
              fontSize: 15,
              color: cs.onSurface.withValues(alpha: 0.6),
              height: 1.5,
            ),
          ),
        ],
      ),
    );
  }

  // Page 2: Region selection
  Widget _buildRegionPage(ColorScheme cs, bool isDark) {
    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(24, 16, 24, 0),
          child: Column(
            children: [
              Icon(Icons.location_on_rounded, size: 36, color: cs.primary),
              const SizedBox(height: 12),
              Text(
                'Оберіть регіони',
                style: GoogleFonts.plusJakartaSans(
                  fontSize: 22,
                  fontWeight: FontWeight.w700,
                  color: cs.onSurface,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                'Ви отримуватимете сповіщення для обраних регіонів',
                textAlign: TextAlign.center,
                style: GoogleFonts.plusJakartaSans(
                  fontSize: 14,
                  color: cs.onSurface.withValues(alpha: 0.5),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),
        Expanded(
          child: ListView.builder(
            padding: const EdgeInsets.symmetric(horizontal: 24),
            itemCount: _regions.length + 1,
            itemBuilder: (context, index) {
              if (index == 0) {
                final allSelected = _selectedRegions.length == _regions.length;
                return Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: Material(
                    color: allSelected
                        ? cs.primary.withValues(alpha: 0.15)
                        : Colors.transparent,
                    borderRadius: BorderRadius.circular(12),
                    child: InkWell(
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
                      borderRadius: BorderRadius.circular(12),
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 16,
                          vertical: 14,
                        ),
                        decoration: BoxDecoration(
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(
                            color: allSelected
                                ? cs.primary.withValues(alpha: 0.4)
                                : cs.outline.withValues(alpha: 0.2),
                            width: allSelected ? 1.5 : 0.5,
                          ),
                        ),
                        child: Row(
                          children: [
                            Icon(
                              Icons.checklist_rounded,
                              size: 20,
                              color: allSelected ? cs.primary : cs.onSurface.withValues(alpha: 0.5),
                            ),
                            const SizedBox(width: 12),
                            Text(
                              'Всі регіони',
                              style: GoogleFonts.plusJakartaSans(
                                fontSize: 15,
                                fontWeight: allSelected ? FontWeight.w600 : FontWeight.w500,
                                color: cs.onSurface,
                              ),
                            ),
                            const Spacer(),
                            if (allSelected)
                              Icon(Icons.check_circle_rounded,
                                  size: 20, color: cs.primary),
                          ],
                        ),
                      ),
                    ),
                  ),
                );
              }
              final region = _regions[index - 1];
              final isSelected = _selectedRegions.contains(region);
              return Padding(
                padding: const EdgeInsets.only(bottom: 6),
                child: Material(
                  color: isSelected
                      ? cs.primary.withValues(alpha: 0.1)
                      : Colors.transparent,
                  borderRadius: BorderRadius.circular(12),
                  child: InkWell(
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
                    borderRadius: BorderRadius.circular(12),
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 16,
                        vertical: 14,
                      ),
                      decoration: BoxDecoration(
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(
                          color: isSelected
                              ? cs.primary.withValues(alpha: 0.3)
                              : cs.outline.withValues(alpha: 0.15),
                          width: isSelected ? 1.5 : 0.5,
                        ),
                      ),
                      child: Row(
                        children: [
                          Text(
                            region,
                            style: GoogleFonts.plusJakartaSans(
                              fontSize: 15,
                              fontWeight: isSelected
                                  ? FontWeight.w600
                                  : FontWeight.w400,
                              color: cs.onSurface,
                            ),
                          ),
                          const Spacer(),
                          if (isSelected)
                            Icon(Icons.check_circle_rounded,
                                size: 20, color: cs.primary),
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
          padding: const EdgeInsets.all(24),
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

  // Page 3: Notification permissions
  Widget _buildNotificationPage(ColorScheme cs, bool isDark) {
    return Padding(
      padding: const EdgeInsets.all(40),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Container(
            width: 100,
            height: 100,
            decoration: BoxDecoration(
              color: cs.error.withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(28),
            ),
            child: Icon(Icons.notifications_active_rounded,
                size: 48, color: cs.error),
          ),
          const SizedBox(height: 48),
          Text(
            'Увімкніть\nсповіщення',
            textAlign: TextAlign.center,
            style: GoogleFonts.plusJakartaSans(
              fontSize: 28,
              fontWeight: FontWeight.w800,
              color: cs.onSurface,
              height: 1.2,
              letterSpacing: -0.5,
            ),
          ),
          const SizedBox(height: 16),
          Text(
            'Це критично для вашої безпеки. Сповіщення про ракети '
            'та дрони приходять миттєво.',
            textAlign: TextAlign.center,
            style: GoogleFonts.plusJakartaSans(
              fontSize: 15,
              color: cs.onSurface.withValues(alpha: 0.6),
              height: 1.5,
            ),
          ),
          const SizedBox(height: 40),
          NeptunButton(
            label: _notificationsGranted
                ? 'Сповіщення увімкнено'
                : 'Увімкнути сповіщення',
            icon: _notificationsGranted
                ? Icons.check_circle_rounded
                : Icons.notifications_rounded,
            isExpanded: true,
            onPressed: _notificationsGranted ? _onNext : _requestNotifications,
          ),
          if (!_notificationsGranted) ...[
            const SizedBox(height: 12),
            TextButton(
              onPressed: _onNext,
              child: Text(
                'Пізніше',
                style: GoogleFonts.plusJakartaSans(
                  fontSize: 14,
                  fontWeight: FontWeight.w500,
                  color: cs.onSurface.withValues(alpha: 0.4),
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }

  // Page 4: Ready
  Widget _buildReadyPage(ColorScheme cs, bool isDark) {
    return Padding(
      padding: const EdgeInsets.all(40),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Container(
            width: 100,
            height: 100,
            decoration: BoxDecoration(
              color: cs.secondary.withValues(alpha: 0.1),
              borderRadius: BorderRadius.circular(28),
            ),
            child: Icon(Icons.rocket_launch_rounded,
                size: 48, color: cs.secondary),
          ),
          const SizedBox(height: 48),
          Text(
            'Все готово!',
            textAlign: TextAlign.center,
            style: GoogleFonts.plusJakartaSans(
              fontSize: 28,
              fontWeight: FontWeight.w800,
              color: cs.onSurface,
              height: 1.2,
            ),
          ),
          const SizedBox(height: 16),
          Text(
            'Карта, радар загроз, модерований чат — '
            'все для вашої безпеки.',
            textAlign: TextAlign.center,
            style: GoogleFonts.plusJakartaSans(
              fontSize: 15,
              color: cs.onSurface.withValues(alpha: 0.6),
              height: 1.5,
            ),
          ),
          const SizedBox(height: 32),
          // Feature list
          ...[
            _buildFeatureRow(Icons.map_rounded, 'Карта в реальному часі', cs),
            _buildFeatureRow(Icons.radar_rounded, 'Радар загроз', cs),
            _buildFeatureRow(Icons.chat_rounded, 'Модерований чат', cs),
            _buildFeatureRow(Icons.notifications_rounded, 'Миттєві сповіщення', cs),
          ],
        ],
      ),
    );
  }

  Widget _buildFeatureRow(IconData icon, String label, ColorScheme cs) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Row(
        children: [
          Icon(icon, size: 20, color: cs.primary),
          const SizedBox(width: 12),
          Text(
            label,
            style: GoogleFonts.plusJakartaSans(
              fontSize: 14,
              fontWeight: FontWeight.w500,
              color: cs.onSurface.withValues(alpha: 0.7),
            ),
          ),
        ],
      ),
    );
  }
}
