import 'dart:async';
import 'dart:io' show Platform;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:google_mobile_ads/google_mobile_ads.dart';
import '../config/prefs_keys.dart';
import '../core/di/service_locator.dart';
import '../services/android_platform_service.dart';
import '../core/widgets/tab_index_scope.dart';
import '../services/ad_service.dart';
import '../services/chat_service.dart';
import '../services/data_stream_service.dart';
import '../services/presence_service.dart';
import '../services/moderator_service.dart';
import '../services/purchase_service.dart';
import '../core/providers/providers.dart';
import '../widgets/offline_banner.dart';
import '../design/design_exports.dart';

/// Main app shell with 4-tab bottom navigation driven by GoRouter StatefulShellRoute.
class AppShell extends ConsumerStatefulWidget {
  final StatefulNavigationShell navigationShell;

  const AppShell({super.key, required this.navigationShell});

  @override
  ConsumerState<AppShell> createState() => AppShellState();
}

class AppShellState extends ConsumerState<AppShell> {
  static const double chromeHeight = 116;
  static const double contentTopGap = 10;

  /// Switch to map tab (index 0) — called from ChatTab back button
  void switchToMap() {
    widget.navigationShell.goBranch(0);
  }

  int _chatOnlineFallback = 0;
  int? _presenceTotal;
  StreamSubscription<int>? _onlineSub;
  StreamSubscription<int>? _presenceSub;
  StreamSubscription<bool>? _modSub;

  // Cache the AdWidget to avoid "already in widget tree" crash
  Widget? _cachedBannerWidget;
  BannerAd? _cachedBannerAd;

  // 7-tap moderator login on logo
  int _logoTapCount = 0;
  DateTime? _lastLogoTap;

  static const _tabTitles = ['Карта', 'Радар', 'Регіони', 'Чат', 'Профіль'];
  static const _tabIcons = [
    Icons.map_rounded,
    Icons.radar_rounded,
    Icons.location_on_rounded,
    Icons.chat_bubble_rounded,
    Icons.person_rounded,
  ];

  @override
  void initState() {
    super.initState();
    final chat = sl<ChatService>();
    _chatOnlineFallback = chat.onlineCount;
    _onlineSub = chat.onlineStream.listen((n) {
      if (mounted) setState(() => _chatOnlineFallback = n);
    });
    sl<PresenceService>().start();
    _presenceSub = sl<PresenceService>().totalStream.listen((n) {
      if (mounted) setState(() => _presenceTotal = n);
    });
    _modSub = ModeratorService.instance.stream.listen((_) {
      if (mounted) setState(() {});
    });
    // Mark session active for App Open Ad safety
    sl<AdService>().markSessionActive();
    // Init moderator service (reads deviceId from SharedPreferences directly)
    sl<ModeratorService>().init();
    // Connect SSE data stream early (alarms + markers push)
    sl<DataStreamService>().connect();
    // Bridge SSE online events → ChatService so counter shows immediately
    chat.connectSSE();

    // Оптимізація батареї на Xiaomi/Huawei — критично для сповіщень
    if (Platform.isAndroid) {
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
    showDialog(
      context: ctx,
      barrierDismissible: true,
      builder: (context) => AlertDialog(
        title: const Row(
          children: [
            Icon(Icons.battery_alert_rounded, color: Colors.orange, size: 28),
            SizedBox(width: 12),
            Expanded(child: Text('Надійні сповіщення')),
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
  void dispose() {
    _onlineSub?.cancel();
    _presenceSub?.cancel();
    _modSub?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final isPremium = sl<PurchaseService>().isPremium;
    final topPadding = MediaQuery.of(context).padding.top;

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
        extendBodyBehindAppBar: true,
        appBar: PreferredSize(
          preferredSize: Size.fromHeight(chromeHeight + topPadding),
          child: _NeptunAppBar(
            title: _tabTitles[widget.navigationShell.currentIndex],
            tabIcon: _tabIcons[widget.navigationShell.currentIndex],
            onlineCount: _presenceTotal ?? _chatOnlineFallback,
            isDark: isDark,
            isPremium: isPremium,
            isModerator: sl<ModeratorService>().isModerator,
            topPadding: topPadding,
            onLogoTap: _onLogoTap,
            onTelegramTap: () => launchUrl(
              Uri.parse('https://t.me/+Q0PcuV4OkuxmYjVi'),
              mode: LaunchMode.externalApplication,
            ),
            onPremiumTap: () => context.push('/premium'),
            onModeratorTap: () => context.push('/chat-admin'),
            onThemeToggle: () {
              HapticFeedback.lightImpact();
              ref.read(themeModeProvider.notifier).toggle();
            },
          ),
        ),
        body: Stack(
          children: [
            TabIndexScope(
              index: widget.navigationShell.currentIndex,
              child: widget.navigationShell,
            ),
            Positioned(
              top: chromeHeight + topPadding,
              left: 0,
              right: 0,
              child: const OfflineBanner(),
            ),
          ],
        ),
        bottomNavigationBar: ListView(
          shrinkWrap: true,
          physics: const NeverScrollableScrollPhysics(),
          children: [
            // ── Banner Ad ──
            if (!isPremium && sl<AdService>().isBannerAdLoaded)
              Builder(
                builder: (_) {
                  final currentAd = sl<AdService>().bannerAd;
                  if (currentAd != null && currentAd != _cachedBannerAd) {
                    _cachedBannerAd = currentAd;
                    _cachedBannerWidget = AdWidget(ad: currentAd);
                  }
                  if (_cachedBannerWidget == null) {
                    return const SizedBox.shrink();
                  }
                  final adHeight = currentAd?.size.height.toDouble() ?? 50;
                  return Container(
                    width: double.infinity,
                    height: adHeight,
                    clipBehavior: Clip.hardEdge,
                    decoration: BoxDecoration(color: cs.surface),
                    alignment: Alignment.center,
                    child: _cachedBannerWidget!,
                  );
                },
              ),
            TacticalNavBar(
              selectedIndex: widget.navigationShell.currentIndex,
              onTap: (i) => widget.navigationShell.goBranch(i),
              destinations: const [
                TacticalNavDestination(
                  icon: Icons.map_outlined,
                  selectedIcon: Icons.map_rounded,
                  label: 'Карта',
                ),
                TacticalNavDestination(
                  icon: Icons.radar_outlined,
                  selectedIcon: Icons.radar_rounded,
                  label: 'Радар',
                ),
                TacticalNavDestination(
                  icon: Icons.chat_bubble_outline_rounded,
                  selectedIcon: Icons.chat_bubble_rounded,
                  label: 'Чат',
                ),
                TacticalNavDestination(
                  icon: Icons.person_outline_rounded,
                  selectedIcon: Icons.person_rounded,
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
      if (sl<ModeratorService>().isModerator) {
        _showModLogoutDialog();
      } else {
        _showModLoginDialog();
      }
    }
  }

  void _showModLoginDialog() {
    final controller = TextEditingController();
    showDialog<String>(
      context: context,
      barrierDismissible: true,
      builder: (ctx) => AlertDialog(
        title: const Text('Модератор'),
        content: TextField(
          controller: controller,
          obscureText: true,
          decoration: const InputDecoration(
            hintText: 'Пароль',
            border: OutlineInputBorder(),
          ),
          autofocus: true,
          onSubmitted: (_) => Navigator.of(ctx).pop(controller.text),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: const Text('Скасувати'),
          ),
          FilledButton(
            onPressed: () => Navigator.of(ctx).pop(controller.text),
            child: const Text('Увійти'),
          ),
        ],
      ),
    ).then((secret) {
      if (secret == null || secret.isEmpty) return;
      // Defer login to next frame so dialog fully closes first (avoids freeze)
      WidgetsBinding.instance.addPostFrameCallback((_) {
        _performModLogin(secret);
      });
    });
  }

  Future<void> _performModLogin(String secret) async {
    final err = await sl<ModeratorService>().login(secret);
    if (!mounted) return;
    if (err != null) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(err)));
    } else {
      setState(() {});
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text('Модератор увійшов')));
    }
  }

  void _showModLogoutDialog() {
    showDialog<bool>(
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
          setState(() {});
          ScaffoldMessenger.of(
            context,
          ).showSnackBar(const SnackBar(content: Text('Модератор вийшов')));
        }
      }
    });
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
  final double topPadding;
  final VoidCallback onLogoTap;
  final VoidCallback onTelegramTap;
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
    required this.topPadding,
    required this.onLogoTap,
    required this.onTelegramTap,
    required this.onPremiumTap,
    this.onModeratorTap,
    required this.onThemeToggle,
  });

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final surfaceColor = isDark ? const Color(0xFF181E2D) : cs.surface;
    final muted = cs.onSurface.withValues(alpha: 0.56);
    final divider = isDark
        ? const Color(0xFF252C3D)
        : cs.outline.withValues(alpha: 0.18);
    return Container(
      padding: EdgeInsets.fromLTRB(14, topPadding + 8, 14, 0),
      decoration: BoxDecoration(
        color: surfaceColor,
        borderRadius: const BorderRadius.vertical(bottom: Radius.circular(24)),
        border: Border(bottom: BorderSide(color: divider, width: 1)),
      ),
      child: SizedBox(
        height: AppShellState.chromeHeight,
        child: Column(
          children: [
            SizedBox(
              height: 66,
              child: Row(
                children: [
                  // ── Left: Logo + Title (7-tap area for moderator) ──
                  Expanded(
                    child: GestureDetector(
                      onTap: onLogoTap,
                      behavior: HitTestBehavior.opaque,
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Dron Alerts',
                            style: GoogleFonts.plusJakartaSans(
                              fontSize: 17,
                              fontWeight: FontWeight.w800,
                              color: cs.onSurface,
                              letterSpacing: 0,
                              height: 1.1,
                            ),
                          ),
                          const SizedBox(height: 6),
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
                                    final curved = CurvedAnimation(
                                      parent: animation,
                                      curve: Curves.easeOutCubic,
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
                                      Icon(tabIcon, size: 15, color: muted),
                                      const SizedBox(width: 5),
                                      Flexible(
                                        child: Text(
                                          title,
                                          maxLines: 1,
                                          overflow: TextOverflow.ellipsis,
                                          style: GoogleFonts.plusJakartaSans(
                                            fontSize: 11,
                                            fontWeight: FontWeight.w700,
                                            color: muted,
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
                                  width: 4,
                                  height: 4,
                                  decoration: BoxDecoration(
                                    color: muted,
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

                  // ── Right: Action chips ──
                  _ActionChip(
                    icon: Icons.send_rounded,
                    isDark: isDark,
                    onTap: onTelegramTap,
                    accentColor: cs.onSurface,
                  ),
                  const SizedBox(width: 6),
                  if (title == 'Чат') ...[
                    _ActionChip(
                      icon: Icons.search_rounded,
                      isDark: isDark,
                      onTap: () {},
                      accentColor: cs.onSurface,
                    ),
                    const SizedBox(width: 6),
                    _ActionChip(
                      icon: Icons.settings_rounded,
                      isDark: isDark,
                      onTap: () => context.push('/chat-settings'),
                      accentColor: cs.onSurface,
                    ),
                    const SizedBox(width: 6),
                  ],
                  if (isModerator) ...[
                    _ActionChip(
                      icon: Icons.admin_panel_settings_rounded,
                      isDark: isDark,
                      onTap: onModeratorTap ?? () {},
                      accentColor: cs.tertiary,
                    ),
                    const SizedBox(width: 6),
                  ],
                  _ProChip(
                    isPremium: isPremium,
                    isDark: isDark,
                    onTap: onPremiumTap,
                  ),
                  const SizedBox(width: 6),
                  _ActionChip(
                    icon: isDark
                        ? Icons.dark_mode_outlined
                        : Icons.light_mode_outlined,
                    isDark: isDark,
                    onTap: onThemeToggle,
                    accentColor: cs.onSurface,
                  ),
                ],
              ),
            ),
            Divider(
              height: 1,
              thickness: 1,
              color: divider.withValues(alpha: 0.6),
            ),
            GestureDetector(
              onTap: onTelegramTap,
              behavior: HitTestBehavior.opaque,
              child: SizedBox(
                height: 42,
                child: Row(
                  children: [
                    Icon(Icons.near_me_outlined, size: 20, color: muted),
                    const SizedBox(width: 12),
                    Expanded(
                      child: Text(
                        'Офіційний Telegram канал',
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: GoogleFonts.plusJakartaSans(
                          fontSize: 13,
                          fontWeight: FontWeight.w800,
                          color: muted,
                          letterSpacing: 0.2,
                        ),
                      ),
                    ),
                    Icon(Icons.chevron_right_rounded, size: 24, color: muted),
                  ],
                ),
              ),
            ),
          ],
        ),
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

  static const _goldDark = Color(0xFFFFB800);
  static const _goldLight = Color(0xFFE5A500);

  @override
  Widget build(BuildContext context) {
    final gold = isDark ? _goldDark : _goldLight;

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
          color: Colors.transparent,
          borderRadius: BorderRadius.circular(22),
          border: Border.all(
            color: isDark ? const Color(0xFFEAF0F8) : gold,
            width: 1.1,
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              isPremium ? Icons.star_rounded : Icons.workspace_premium_rounded,
              size: 18,
              color: isDark ? const Color(0xFFEAF0F8) : gold,
            ),
            const SizedBox(width: 6),
            Text(
              'PRO',
              style: GoogleFonts.plusJakartaSans(
                fontSize: 12,
                fontWeight: FontWeight.w800,
                color: isDark ? const Color(0xFFEAF0F8) : gold,
                letterSpacing: 0.5,
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
                  ? const Color(0xFF252B3A)
                  : Colors.black.withValues(alpha: 0.04),
              borderRadius: BorderRadius.circular(20),
              border: Border.all(
                color: isDark
                    ? const Color(0xFF30384A)
                    : Colors.black.withValues(alpha: 0.05),
                width: 1,
              ),
            ),
            child: Icon(
              icon,
              size: 22,
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
    final color = colorScheme.secondary;
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 6,
          height: 6,
          decoration: BoxDecoration(
            color: color,
            shape: BoxShape.circle,
            boxShadow: [
              BoxShadow(
                color: color.withValues(alpha: 0.5),
                blurRadius: 3,
                spreadRadius: 0,
              ),
            ],
          ),
        ),
        const SizedBox(width: 4),
        ConstrainedBox(
          constraints: const BoxConstraints(minWidth: 22),
          child: Text(
            '$count',
            style: GoogleFonts.plusJakartaSans(
              fontSize: 11,
              fontWeight: FontWeight.w600,
              color: color.withValues(alpha: 0.9),
            ),
          ),
        ),
      ],
    );
  }
}
