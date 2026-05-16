import 'dart:async';
import 'dart:io' show Platform;
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../core/utils/open_neptun_telegram.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:lucide_icons_flutter/lucide_icons.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:google_mobile_ads/google_mobile_ads.dart';
import '../config/prefs_keys.dart';
import '../config/app_constants.dart';
import '../core/di/service_locator.dart';
import '../services/android_platform_service.dart';
import '../core/widgets/tab_index_scope.dart';
import '../services/ad_service.dart';
import '../services/chat_service.dart';
import '../services/data_stream_service.dart';
import '../services/moderator_service.dart';
import '../services/purchase_service.dart';
import '../core/providers/providers.dart';
import '../widgets/offline_banner.dart';
import 'chat_settings_page.dart';
import '../design/design_exports.dart';
import '../core/widgets/neptun_overlay_insets.dart';
import '../core/widgets/neptun_shell_modal.dart';

/// Main app shell with bottom navigation (Карта | Радар | Чат | Профіль) driven by GoRouter StatefulShellRoute.
class AppShell extends ConsumerStatefulWidget {
  final StatefulNavigationShell navigationShell;

  const AppShell({super.key, required this.navigationShell});

  @override
  ConsumerState<AppShell> createState() => AppShellState();
}

class AppShellState extends ConsumerState<AppShell> {
  // Cache the AdWidget to avoid "already in widget tree" crash
  Widget? _cachedBannerWidget;
  BannerAd? _cachedBannerAd;

  // 7-tap moderator login on logo
  int _logoTapCount = 0;
  DateTime? _lastLogoTap;

  static const _tabTitles = ['Карта', 'Радар', 'Чат', 'Профіль'];
  static const _tabIcons = [
    LucideIcons.map,
    LucideIcons.radar,
    LucideIcons.messageCircle,
    LucideIcons.userRound,
  ];

  @override
  void initState() {
    super.initState();
    final chat = sl<ChatService>();
    // Mark session active for App Open Ad safety
    sl<AdService>().markSessionActive();
    // Init moderator service (reads deviceId from SharedPreferences directly)
    sl<ModeratorService>().init();
    // Connect SSE data stream early (alarms + markers push)
    sl<DataStreamService>().connect();
    // Bridge SSE online events → ChatService so counter shows immediately
    chat.connectSSE();

    // Оптимізація батареї на Xiaomi/Huawei — критично для сповіщень
    if (!kIsWeb && Platform.isAndroid) {
      Future.delayed(
        const Duration(seconds: 3),
        () => _maybeShowBatteryOptPrompt(),
      );
    }
  }

  Future<void> _maybeShowBatteryOptPrompt() async {
    if (!mounted) return;
    final android = AndroidPlatformService();
    if (!android.needsBatteryOptimizationWarning) return;
    final disabled = await android.isBatteryOptimizationDisabled();
    if (disabled) return;

    final prefs = sl<SharedPreferences>();
    final lastShown = prefs.getInt(PrefsKeys.batteryOptPromptLastShown) ?? 0;
    const days7 = 7 * 24 * 60 * 60 * 1000;
    if (DateTime.now().millisecondsSinceEpoch - lastShown < days7) return;

    if (!mounted) return;
    final ctx = context;
    await prefs.setInt(
      PrefsKeys.batteryOptPromptLastShown,
      DateTime.now().millisecondsSinceEpoch,
    );
    if (!ctx.mounted) return;
    _showBatteryOptDialog(ctx);
  }

  void _showBatteryOptDialog(BuildContext ctx) {
    NeptunShellModal.showDialog(
      context: ctx,
      barrierDismissible: true,
      builder: (context) => AlertDialog(
        title: Row(
          children: [
            Icon(
              Icons.battery_alert_rounded,
              color: Theme.of(context).colorScheme.onSurface,
              size: 28,
            ),
            const SizedBox(width: 12),
            const Expanded(child: Text('Надійні сповіщення')),
          ],
        ),
        content: const Text(
          'На вашому пристрої увімкнена оптимізація батареї. Це може затримувати сповіщення про тривоги.\n\nВимкніть оптимізацію для додатку, щоб отримувати сповіщення вчасно.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Пізніше'),
          ),
          FilledButton(
            onPressed: () {
              Navigator.of(context).pop();
              HapticFeedback.mediumImpact();
              AndroidPlatformService().requestDisableBatteryOptimization();
            },
            child: const Text('Вимкнути оптимізацію'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    // Реклама: окремий [ListenableBuilder] нижче — щоб [bannerRebuildTick] не
    // перебудовував карту/WebView і весь [Expanded].
    return ListenableBuilder(
      listenable: Listenable.merge([
        sl<PurchaseService>().premiumNotifier,
        sl<ModeratorService>().isModeratorNotifier,
      ]),
      builder: (context, _) => _buildShellChromeAndTabs(context),
    );
  }

  /// Ряд банера: лише AdMob tick (+ батьківський rebuild при premium/mod).
  Widget _buildBannerAdStrip(BuildContext context, ColorScheme cs) {
    final isPremium = sl<PurchaseService>().isPremium;
    final adSvc = sl<AdService>();
    final hasAd = !isPremium && adSvc.isBannerAdLoaded;
    final currentAd = adSvc.bannerAd;
    if (currentAd == null) {
      _cachedBannerAd = null;
      _cachedBannerWidget = null;
    } else if (currentAd != _cachedBannerAd) {
      _cachedBannerAd = currentAd;
      _cachedBannerWidget = AdWidget(ad: currentAd);
    }
    if (!hasAd || _cachedBannerWidget == null) {
      return const SizedBox.shrink();
    }
    final adHeight = currentAd?.size.height.toDouble() ?? 50.0;
    return Container(
      width: double.infinity,
      height: adHeight,
      clipBehavior: Clip.hardEdge,
      decoration: BoxDecoration(
        color: cs.surface.withValues(alpha: 0.92),
        border: Border(
          top: BorderSide(
            color: cs.outline.withValues(alpha: 0.12),
            width: 0.5,
          ),
        ),
      ),
      alignment: Alignment.center,
      child: RepaintBoundary(child: _cachedBannerWidget!),
    );
  }

  Widget _buildShellChromeAndTabs(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final isPremium = sl<PurchaseService>().isPremium;
    final mq = MediaQuery.of(context);
    final viewTop = mq.viewPadding.top;
    final bottomViewInset = mq.viewPadding.bottom;

    final hudH = NeptunShellChrome.hudCardBodyHeight;
    final contentTop =
        viewTop +
        NeptunShellChrome.hudTopMargin +
        hudH +
        NeptunShellChrome.contentGapBelowHud;
    // Реклама й таббар винесені в [Column] під [Expanded] з контентом табів — вони
    // більше не перекривають overlay вкладеного Navigator (шити/діалоги без root).
    // Нижній inset для скролу лише «дихання» в кінці списків; safe area знизу вже в [TacticalNavBar].
    final contentBottom = NeptunSpacing.xxxl;

    return AnnotatedRegion<SystemUiOverlayStyle>(
      value: SystemUiOverlayStyle(
        statusBarColor: Colors.transparent,
        statusBarIconBrightness: isDark ? Brightness.light : Brightness.dark,
        systemNavigationBarColor: cs.surface,
        systemNavigationBarIconBrightness: isDark
            ? Brightness.light
            : Brightness.dark,
      ),
      child: Scaffold(
        extendBody: true,
        extendBodyBehindAppBar: true,
        body: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Expanded(
              child: Stack(
                clipBehavior: Clip.none,
                children: [
                  NeptunOverlayInsets(
                    contentTop: contentTop,
                    contentBottom: contentBottom,
                    child: RepaintBoundary(
                      child: TabIndexScope(
                        index: widget.navigationShell.currentIndex,
                        child: widget.navigationShell,
                      ),
                    ),
                  ),
                  Positioned(
                    top: NeptunShellChrome.hudTopMargin,
                    left: 0,
                    right: 0,
                    child: _ThrottledOnlineAppBar(
                      title: _tabTitles[widget.navigationShell.currentIndex],
                      tabIcon: _tabIcons[widget.navigationShell.currentIndex],
                      isDark: isDark,
                      isPremium: isPremium,
                      isModerator: sl<ModeratorService>().isModerator,
                      showChatActions: widget.navigationShell.currentIndex == 2,
                      onChatSearch: () {
                        HapticFeedback.lightImpact();
                        ref
                            .read(chatControllerProvider.notifier)
                            .setSearchMode(true);
                      },
                      onChatSettings: () => _openChatSettings(context),
                      onLogoTap: _onLogoTap,
                      onTelegramTap: () => openNeptunTelegramChannel('app_bar'),
                      onTelegramSublineTap: () =>
                          openNeptunTelegramChannel('app_bar_subline'),
                      onPremiumTap: () => context.push('/premium'),
                      onModeratorTap: () => context.push('/chat-admin'),
                      onThemeToggle: () =>
                          ref.read(themeModeProvider.notifier).toggle(),
                    ),
                  ),
                  Positioned(
                    top: viewTop + NeptunShellChrome.hudTopMargin + hudH + 4,
                    left: 0,
                    right: 0,
                    child: const RepaintBoundary(child: OfflineBanner()),
                  ),
                ],
              ),
            ),
            ListenableBuilder(
              listenable: sl<AdService>().bannerRebuildTick,
              builder: (context, _) => _buildBannerAdStrip(context, cs),
            ),
            TacticalNavBar(
              floating: false,
              bottomViewInset: bottomViewInset,
              selectedIndex: widget.navigationShell.currentIndex,
              onTap: (i) {
                final from = widget.navigationShell.currentIndex;
                sl<AdService>().onMainShellTabChanged(
                  fromIndex: from,
                  toIndex: i,
                );
                widget.navigationShell.goBranch(i);
              },
              destinations: const [
                TacticalNavDestination(
                  icon: Icons.map_outlined,
                  selectedIcon: Icons.map,
                  label: 'Карта',
                ),
                TacticalNavDestination(
                  icon: Icons.radar_outlined,
                  selectedIcon: Icons.radar,
                  label: 'Радар',
                ),
                TacticalNavDestination(
                  icon: Icons.chat_bubble_outline,
                  selectedIcon: Icons.chat_bubble,
                  label: 'Чат',
                ),
                TacticalNavDestination(
                  icon: Icons.person_outline,
                  selectedIcon: Icons.person,
                  label: 'Профіль',
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  /// 7-tap on logo → moderator login (if not mod) or logout (if mod)
  void _onLogoTap() {
    HapticFeedback.selectionClick();
    final now = DateTime.now();
    const window = Duration(seconds: 3);
    if (_lastLogoTap != null && now.difference(_lastLogoTap!) > window) {
      _logoTapCount = 0;
    }
    _lastLogoTap = now;
    _logoTapCount++;
    if (_logoTapCount >= 7) {
      _logoTapCount = 0;
      // Next frame: avoids iOS freeze opening modal + keyboard in the same gesture
      // as the 7th tap (heavy body e.g. map under extendBodyBehindAppBar).
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (!mounted) return;
        if (sl<ModeratorService>().isModerator) {
          _showModLogoutDialog();
        } else {
          _showModLoginDialog();
        }
      });
    }
  }

  void _openChatSettings(BuildContext context) {
    HapticFeedback.lightImpact();
    if (!context.mounted) return;
    // Без postFrameCallback — відкриття одразу після тапу.
    // Легкий fade замість fullscreenDialog (коротша анімація, менше роботи на перший кадр).
    Navigator.of(context, rootNavigator: true).push<void>(
      PageRouteBuilder<void>(
        opaque: true,
        barrierDismissible: false,
        pageBuilder: (ctx, animation, secondaryAnimation) =>
            const ChatSettingsPage(),
        transitionDuration: const Duration(milliseconds: 180),
        reverseTransitionDuration: const Duration(milliseconds: 160),
        transitionsBuilder: (ctx, animation, secondaryAnimation, child) {
          return FadeTransition(opacity: animation, child: child);
        },
      ),
    );
  }

  void _showModLoginDialog() {
    NeptunShellModal.showDialog<String>(
      context: context,
      barrierDismissible: true,
      builder: (_) => const _ModPasswordDialog(),
    ).then((secret) {
      if (secret == null || secret.isEmpty) return;
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) _performModLogin(secret);
      });
    });
  }

  Future<void> _performModLogin(String secret) async {
    final err = await sl<ModeratorService>().login(secret);
    if (!mounted) return;
    if (err != null) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(err)));
    } else {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text('Модератор увійшов')));
    }
  }

  void _showModLogoutDialog() {
    NeptunShellModal.showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Модератор'),
        content: const Text('Вийти з режиму модератора?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: const Text('Ні'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(ctx).pop(true),
            child: const Text('Так'),
          ),
        ],
      ),
    ).then((ok) async {
      if (ok == true) {
        await sl<ModeratorService>().logout();
        if (mounted) {
          ScaffoldMessenger.of(
            context,
          ).showSnackBar(const SnackBar(content: Text('Модератор вийшов')));
        }
      }
    });
  }
}

/// Owns [TextEditingController] / [FocusNode] so nothing is disposed while the
/// field is still mounted; focus is requested post-frame (not [autofocus]) to
/// reduce keyboard/platform-view deadlocks over the map tab on iOS.
class _ModPasswordDialog extends StatefulWidget {
  const _ModPasswordDialog();

  @override
  State<_ModPasswordDialog> createState() => _ModPasswordDialogState();
}

class _ModPasswordDialogState extends State<_ModPasswordDialog> {
  final _controller = TextEditingController();
  final _focusNode = FocusNode();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) _focusNode.requestFocus();
    });
  }

  @override
  void dispose() {
    _focusNode.dispose();
    _controller.dispose();
    super.dispose();
  }

  void _submit() => Navigator.of(context).pop(_controller.text.trim());

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Модератор'),
      content: TextField(
        controller: _controller,
        focusNode: _focusNode,
        obscureText: true,
        maxLength: ModeratorService.maxModeratorSecretLength,
        decoration: const InputDecoration(
          hintText: 'Пароль',
          border: OutlineInputBorder(),
          counterText: '',
        ),
        autofocus: false,
        onSubmitted: (_) => _submit(),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Скасувати'),
        ),
        FilledButton(onPressed: _submit, child: const Text('Увійти')),
      ],
    );
  }
}

// ═════════════════════════════════════════════════════════════════════════
// Online count: throttle stream so AppShell / tab body does not rebuild every tick.
// ═════════════════════════════════════════════════════════════════════════
class _ThrottledOnlineAppBar extends StatefulWidget {
  final String title;
  final IconData tabIcon;
  final bool isDark;
  final bool isPremium;
  final bool isModerator;

  /// Вкладка «Чат»: пошук і налаштування перенесені в глобальний HUD.
  final bool showChatActions;
  final VoidCallback? onChatSearch;
  final VoidCallback? onChatSettings;
  final VoidCallback onLogoTap;
  final VoidCallback onTelegramTap;
  final VoidCallback onTelegramSublineTap;
  final VoidCallback onPremiumTap;
  final VoidCallback? onModeratorTap;
  final VoidCallback onThemeToggle;

  const _ThrottledOnlineAppBar({
    required this.title,
    required this.tabIcon,
    required this.isDark,
    required this.isPremium,
    required this.isModerator,
    this.showChatActions = false,
    this.onChatSearch,
    this.onChatSettings,
    required this.onLogoTap,
    required this.onTelegramTap,
    required this.onTelegramSublineTap,
    required this.onPremiumTap,
    this.onModeratorTap,
    required this.onThemeToggle,
  });

  @override
  State<_ThrottledOnlineAppBar> createState() => _ThrottledOnlineAppBarState();
}

class _ThrottledOnlineAppBarState extends State<_ThrottledOnlineAppBar> {
  static const _throttle = Duration(milliseconds: 400);

  late int _onlineCount;
  int _pending = 0;
  Timer? _timer;
  StreamSubscription<int>? _sub;

  @override
  void initState() {
    super.initState();
    final chat = sl<ChatService>();
    _onlineCount = chat.onlineCount;
    _pending = _onlineCount;
    _sub = chat.onlineStream.listen(_onOnline);
  }

  void _onOnline(int n) {
    _pending = n;
    if (_timer?.isActive ?? false) return;
    if (n != _onlineCount) setState(() => _onlineCount = n);
    _timer = Timer(_throttle, () {
      _timer = null;
      if (!mounted) return;
      if (_pending != _onlineCount) setState(() => _onlineCount = _pending);
    });
  }

  @override
  void dispose() {
    _timer?.cancel();
    _sub?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return _NeptunAppBar(
      title: widget.title,
      tabIcon: widget.tabIcon,
      onlineCount: _onlineCount,
      isDark: widget.isDark,
      isPremium: widget.isPremium,
      isModerator: widget.isModerator,
      showChatActions: widget.showChatActions,
      onChatSearch: widget.onChatSearch,
      onChatSettings: widget.onChatSettings,
      onLogoTap: widget.onLogoTap,
      onTelegramTap: widget.onTelegramTap,
      onTelegramSublineTap: widget.onTelegramSublineTap,
      onPremiumTap: widget.onPremiumTap,
      onModeratorTap: widget.onModeratorTap,
      onThemeToggle: widget.onThemeToggle,
    );
  }
}

// ═════════════════════════════════════════════════════════════════════════
// NEPTUN APP BAR — clean, minimal, premium
// ═════════════════════════════════════════════════════════════════════════
class _NeptunAppBar extends StatelessWidget {
  final String title;
  final IconData tabIcon;
  final int onlineCount;
  final bool isDark;
  final bool isPremium;
  final bool isModerator;
  final bool showChatActions;
  final VoidCallback? onChatSearch;
  final VoidCallback? onChatSettings;
  final VoidCallback onLogoTap;
  final VoidCallback onTelegramTap;
  final VoidCallback onTelegramSublineTap;
  final VoidCallback onPremiumTap;
  final VoidCallback? onModeratorTap;
  final VoidCallback onThemeToggle;

  const _NeptunAppBar({
    required this.title,
    required this.tabIcon,
    required this.onlineCount,
    required this.isDark,
    required this.isPremium,
    required this.isModerator,
    this.showChatActions = false,
    this.onChatSearch,
    this.onChatSettings,
    required this.onLogoTap,
    required this.onTelegramTap,
    required this.onTelegramSublineTap,
    required this.onPremiumTap,
    this.onModeratorTap,
    required this.onThemeToggle,
  });

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final titleColor = isDark
        ? NeptunFloatingChrome.darkTitleOnPanel
        : cs.onSurface;
    final subColor = isDark
        ? NeptunFloatingChrome.darkSubtitleOnPanel
        : cs.onSurface;

    final viewTop = MediaQuery.viewPaddingOf(context).top;
    return NeptunFloatingPanel(
      shellChrome: true,
      borderRadiusOverride: const BorderRadius.only(
        bottomLeft: Radius.circular(NeptunFloatingChrome.radiusShell),
        bottomRight: Radius.circular(NeptunFloatingChrome.radiusShell),
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          SizedBox(height: viewTop),
          SizedBox(
            height: 54,
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 14),
              child: Row(
                children: [
                  // ── Left: Title (7-tap area for moderator) ──
                  Expanded(
                    child: GestureDetector(
                      onTap: onLogoTap,
                      behavior: HitTestBehavior.opaque,
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            AppConstants.appName,
                            style: GoogleFonts.plusJakartaSans(
                              fontSize: 15,
                              fontWeight: FontWeight.w800,
                              color: titleColor,
                              letterSpacing: 0.5,
                              height: 1.1,
                            ),
                          ),
                          const SizedBox(height: 1),
                          Row(
                            children: [
                              Flexible(
                                child: AnimatedSwitcher(
                                  duration:
                                      MediaQuery.disableAnimationsOf(context)
                                      ? Duration.zero
                                      : const Duration(milliseconds: 260),
                                  switchInCurve: Curves.easeOutCubic,
                                  switchOutCurve: Curves.easeInCubic,
                                  transitionBuilder: (child, animation) {
                                    final curved = animation.drive(
                                      CurveTween(curve: Curves.easeOutCubic),
                                    );
                                    return FadeTransition(
                                      opacity: curved,
                                      child: SlideTransition(
                                        position: Tween<Offset>(
                                          begin: const Offset(0, 0.12),
                                          end: Offset.zero,
                                        ).animate(curved),
                                        child: child,
                                      ),
                                    );
                                  },
                                  child: Row(
                                    key: ValueKey<String>('$title-$tabIcon'),
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      Icon(
                                        tabIcon,
                                        size: 12,
                                        color: isDark
                                            ? NeptunFloatingChrome
                                                  .darkSubtitleOnPanel
                                            : cs.primary.withValues(
                                                alpha: 0.75,
                                              ),
                                      ),
                                      const SizedBox(width: 4),
                                      Flexible(
                                        child: Text(
                                          title,
                                          maxLines: 1,
                                          overflow: TextOverflow.ellipsis,
                                          style: GoogleFonts.plusJakartaSans(
                                            fontSize: 11,
                                            fontWeight: FontWeight.w500,
                                            color: subColor.withValues(
                                              alpha: 0.85,
                                            ),
                                            letterSpacing: 0.2,
                                          ),
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                              ),
                              if (onlineCount > 0) ...[
                                Container(
                                  margin: const EdgeInsets.symmetric(
                                    horizontal: 6,
                                  ),
                                  width: 2,
                                  height: 2,
                                  decoration: BoxDecoration(
                                    color: subColor.withValues(alpha: 0.35),
                                    shape: BoxShape.circle,
                                  ),
                                ),
                                _OnlineIndicator(
                                  isDark: isDark,
                                  count: onlineCount,
                                  colorScheme: cs,
                                ),
                              ],
                            ],
                          ),
                        ],
                      ),
                    ),
                  ),

                  // ── Right: Action chips (scroll on narrow screens — avoids negative flex / invalid constraints)
                  Flexible(
                    flex: 0,
                    fit: FlexFit.loose,
                    child: SingleChildScrollView(
                      scrollDirection: Axis.horizontal,
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Tooltip(
                            message: 'Telegram — новини та алерти швидше',
                            child: _ActionChip(
                              icon: LucideIcons.send,
                              isDark: isDark,
                              onTap: onTelegramTap,
                              accentColor: cs.onSurface,
                            ),
                          ),
                          const SizedBox(width: 8),
                          if (showChatActions &&
                              onChatSearch != null &&
                              onChatSettings != null) ...[
                            Tooltip(
                              message: 'Пошук у чаті',
                              child: _ActionChip(
                                icon: LucideIcons.search,
                                isDark: isDark,
                                onTap: onChatSearch!,
                                accentColor: cs.onSurface,
                              ),
                            ),
                            const SizedBox(width: 8),
                            Tooltip(
                              message: 'Налаштування чату',
                              child: _ActionChip(
                                icon: LucideIcons.settings,
                                isDark: isDark,
                                onTap: onChatSettings!,
                                accentColor: cs.onSurface,
                              ),
                            ),
                            const SizedBox(width: 8),
                          ],
                          if (isModerator) ...[
                            _ActionChip(
                              icon: LucideIcons.shieldCheck,
                              isDark: isDark,
                              onTap: onModeratorTap ?? () {},
                              accentColor: cs.onSurface,
                            ),
                            const SizedBox(width: 8),
                          ],
                          _ProChip(
                            isPremium: isPremium,
                            isDark: isDark,
                            onTap: onPremiumTap,
                          ),
                          const SizedBox(width: 8),
                          _ThemeToggleChip(
                            isDark: isDark,
                            accentColor: cs.onSurface,
                            onTap: onThemeToggle,
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 14),
            child: Divider(
              height: 1,
              thickness: 1,
              color: cs.outline.withValues(alpha: isDark ? 0.14 : 0.1),
            ),
          ),
          // Integrated Telegram Subline
          Material(
            color: Colors.transparent,
            child: InkWell(
              onTap: onTelegramSublineTap,
              child: Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: 14,
                  vertical: 8,
                ),
                child: Row(
                  children: [
                    Icon(
                      LucideIcons.send,
                      size: 15,
                      color: cs.onSurface.withValues(alpha: 0.55),
                    ),
                    const SizedBox(width: 8),
                    Expanded(
                      child: Text(
                        'Офіційний Telegram канал',
                        style: GoogleFonts.plusJakartaSans(
                          fontSize: 11,
                          fontWeight: FontWeight.w600,
                          color: cs.onSurface.withValues(alpha: 0.72),
                          letterSpacing: 0.06 * 11,
                        ),
                      ),
                    ),
                    Icon(
                      LucideIcons.chevronRight,
                      size: 17,
                      color: cs.onSurface.withValues(alpha: 0.35),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// ═════════════════════════════════════════════════════════════════════════
// PRO CHIP — gold premium button with label
// ═════════════════════════════════════════════════════════════════════════
class _ProChip extends StatelessWidget {
  final bool isPremium;
  final bool isDark;
  final VoidCallback onTap;

  const _ProChip({
    required this.isPremium,
    required this.isDark,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;

    return GestureDetector(
      onTap: () {
        HapticFeedback.selectionClick();
        onTap();
      },
      behavior: HitTestBehavior.opaque,
      child: Container(
        height: 38,
        padding: const EdgeInsets.symmetric(horizontal: 12),
        decoration: BoxDecoration(
          color: isPremium ? Colors.transparent : cs.primary,
          borderRadius: BorderRadius.circular(999),
          border: Border.all(color: cs.primary, width: 1),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              isPremium ? LucideIcons.sparkles : LucideIcons.crown,
              size: 16,
              color: isPremium ? cs.primary : cs.onPrimary,
            ),
            const SizedBox(width: 4),
            Text(
              'PRO',
              style: GoogleFonts.plusJakartaSans(
                fontSize: 11,
                fontWeight: FontWeight.w600,
                color: isPremium ? cs.primary : cs.onPrimary,
                letterSpacing: 0.06 * 11,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ═════════════════════════════════════════════════════════════════════════
// TAP-ABLE ACTION CHIP — subtle circle with icon
// ═════════════════════════════════════════════════════════════════════════

// THEME TOGGLE — sun/moon (плавна зміна іконки, як у Material theme)
class _ThemeToggleChip extends StatelessWidget {
  final bool isDark;
  final Color accentColor;
  final VoidCallback onTap;

  const _ThemeToggleChip({
    required this.isDark,
    required this.accentColor,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: () {
        HapticFeedback.selectionClick();
        onTap();
      },
      behavior: HitTestBehavior.opaque,
      child: Container(
        width: 38,
        height: 38,
        decoration: BoxDecoration(
          color: isDark
              ? Colors.white.withValues(alpha: 0.065)
              : Colors.black.withValues(alpha: 0.045),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(
            color: isDark
                ? Colors.white.withValues(alpha: 0.08)
                : Colors.black.withValues(alpha: 0.06),
            width: 0.5,
          ),
        ),
        child: AnimatedSwitcher(
          duration: AppConstants.themeSwitchDuration,
          switchInCurve: AppConstants.themeSwitchCurve,
          switchOutCurve: AppConstants.themeSwitchCurve,
          transitionBuilder: (child, animation) {
            return ScaleTransition(
              scale: Tween<double>(begin: 0.72, end: 1.0).animate(animation),
              child: FadeTransition(opacity: animation, child: child),
            );
          },
          child: Icon(
            isDark ? LucideIcons.moon : LucideIcons.sun,
            key: ValueKey<bool>(isDark),
            size: 20,
            color: accentColor.withValues(alpha: isDark ? 0.9 : 1.0),
          ),
        ),
      ),
    );
  }
}

class _ActionChip extends StatelessWidget {
  final IconData icon;
  final bool isDark;
  final VoidCallback onTap;
  final Color accentColor;

  const _ActionChip({
    required this.icon,
    required this.isDark,
    required this.onTap,
    required this.accentColor,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: () {
        HapticFeedback.selectionClick();
        onTap();
      },
      behavior: HitTestBehavior.opaque,
      child: Stack(
        clipBehavior: Clip.none,
        children: [
          Container(
            width: 38,
            height: 38,
            decoration: BoxDecoration(
              color: isDark
                  ? Colors.white.withValues(alpha: 0.065)
                  : Colors.black.withValues(alpha: 0.045),
              borderRadius: BorderRadius.circular(14),
              border: Border.all(
                color: isDark
                    ? Colors.white.withValues(alpha: 0.08)
                    : Colors.black.withValues(alpha: 0.06),
                width: 0.5,
              ),
            ),
            child: Icon(
              icon,
              size: 20,
              color: accentColor.withValues(alpha: isDark ? 0.9 : 1.0),
            ),
          ),
        ],
      ),
    );
  }
}

// ═════════════════════════════════════════════════════════════════════════
// ONLINE INDICATOR — green dot + count, stable layout (no jump on change)
// ═════════════════════════════════════════════════════════════════════════
class _OnlineIndicator extends StatelessWidget {
  final bool isDark;
  final int count;
  final ColorScheme colorScheme;

  const _OnlineIndicator({
    required this.isDark,
    required this.count,
    required this.colorScheme,
  });

  @override
  Widget build(BuildContext context) {
    final dotColor = colorScheme.onSurface.withValues(alpha: 0.55);
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 6,
          height: 6,
          decoration: BoxDecoration(color: dotColor, shape: BoxShape.circle),
        ),
        const SizedBox(width: 4),
        ConstrainedBox(
          constraints: const BoxConstraints(minWidth: 22),
          child: Text(
            '$count',
            style: GoogleFonts.plusJakartaSans(
              fontSize: 11,
              fontWeight: FontWeight.w600,
              color: dotColor,
            ),
          ),
        ),
      ],
    );
  }
}
