import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../../core/router/route_paths.dart';
import '../../core/utils/open_neptun_telegram.dart';
import '../../core/di/service_locator.dart';
import '../../services/moderator_service.dart';
import '../../services/purchase_service.dart';
import '../../config/app_constants.dart';
import '../../core/widgets/neptun_overlay_insets.dart';
import '../../core/widgets/neptun_shell_modal.dart';
import '../../design/design_exports.dart';
import '../../features/regions/presentation/regions_selection_provider.dart';
import '../../widgets/profile_nav_tile.dart';
import '../../widgets/profile_notification_quick_card.dart';
import '../../widgets/settings_section.dart';

/// Profile tab — hero → Premium → Сповіщення → Посилання → PRO → модерація.
/// Каркас як у [RadarTab]: [NeptunTabPageScaffold] + [CustomScrollView].
/// Регіони для «Мій регіон»: [regionsSelectionProvider] — той самий екран у вкладці «Радар» → «Регіони».
const double _kProfileCardRadius = 28;

class ProfileTab extends ConsumerStatefulWidget {
  const ProfileTab({super.key});

  @override
  ConsumerState<ProfileTab> createState() => _ProfileTabState();
}

class _ProfileTabState extends ConsumerState<ProfileTab>
    with AutomaticKeepAliveClientMixin {
  @override
  bool get wantKeepAlive => true;

  String _nickname = '';
  bool _isPremium = false;

  @override
  void initState() {
    super.initState();
    _loadSettings();
  }

  Future<void> _loadSettings() async {
    final prefs = await SharedPreferences.getInstance();
    final premium = sl<PurchaseService>().isPremium;
    if (mounted) {
      setState(() {
        _nickname = prefs.getString('chat_nickname') ?? '';
        _isPremium = premium;
      });
    }
  }

  Future<void> _onRefresh() async {
    await _loadSettings();
    await ref.read(regionsSelectionProvider.notifier).reload();
  }

  Color _glassBorderColor(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final cs = Theme.of(context).colorScheme;
    return isDark
        ? Colors.white.withValues(alpha: 0.08)
        : cs.outline.withValues(alpha: 0.35);
  }

  /// Dark: скляний шар поверх S3. Light: піднята поверхня з [ColorScheme] — не [NeptunSurfaces] (темні токени).
  Color _glassFillColor(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final cs = Theme.of(context).colorScheme;
    if (isDark) {
      return NeptunSurfaces.s3.withValues(alpha: 0.6);
    }
    return cs.surfaceContainerHighest;
  }

  void _openGeneralSettingsSheet(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    NeptunShellModal.showBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => DraggableScrollableSheet(
        initialChildSize: 0.92,
        minChildSize: 0.45,
        maxChildSize: 0.96,
        builder: (context, scrollController) {
          return Container(
            decoration: BoxDecoration(
              color: cs.surface,
              borderRadius: const BorderRadius.vertical(
                top: Radius.circular(_kProfileCardRadius),
              ),
            ),
            child: Column(
              children: [
                Padding(
                  padding: const EdgeInsets.fromLTRB(8, 8, 8, 0),
                  child: Row(
                    children: [
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          'Загальні налаштування',
                          style: GoogleFonts.plusJakartaSans(
                            fontSize: 18,
                            fontWeight: FontWeight.w700,
                            color: cs.onSurface,
                          ),
                        ),
                      ),
                      IconButton(
                        onPressed: () => Navigator.of(ctx).pop(),
                        icon: const Icon(Icons.close_rounded),
                        tooltip: 'Закрити',
                      ),
                    ],
                  ),
                ),
                Expanded(
                  child: SingleChildScrollView(
                    controller: scrollController,
                    padding: const EdgeInsets.fromLTRB(
                      NeptunSpacing.screenHorizontal,
                      0,
                      NeptunSpacing.screenHorizontal,
                      NeptunSpacing.xxxl,
                    ),
                    child: const SettingsSection(omitQuickProfileToggles: true),
                  ),
                ),
              ],
            ),
          );
        },
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    super.build(context);
    final cs = Theme.of(context).colorScheme;
    final regions = ref.watch(regionsSelectionProvider);
    final topInset = neptunContentTopPadding(context) + NeptunSpacing.md;
    final bottomInset = neptunContentBottomPadding(context);
    final h = NeptunSpacing.screenHorizontal;

    final regionSubtitle = regions.isLoading
        ? 'Завантаження…'
        : regions.selected.isEmpty
            ? 'Не обрано жодного регіону'
            : 'Обрано позицій: ${regions.selected.length}';

    return NeptunTabPageScaffold(
      body: RefreshIndicator(
        onRefresh: _onRefresh,
        color: cs.primary,
        backgroundColor: cs.surfaceContainerHighest,
        child: CustomScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          slivers: [
            SliverPadding(
              padding: EdgeInsets.fromLTRB(h, topInset, h, bottomInset),
              sliver: SliverList(
                delegate: SliverChildListDelegate([
                  _buildHeroHeader(cs),
                  const SizedBox(height: 20),
                  _buildPremiumHeroContent(cs),
                  const SizedBox(height: 28),
                  SectionHeader(
                    title: 'Сповіщення',
                    icon: Icons.notifications_rounded,
                    padding: const EdgeInsets.fromLTRB(
                      0,
                      0,
                      0,
                      NeptunSpacing.sectionTitleToContent,
                    ),
                  ),
                  NeptunCard(
                    padding: EdgeInsets.zero,
                    borderRadius: _kProfileCardRadius,
                    backgroundColor: _glassFillColor(context),
                    borderColor: _glassBorderColor(context),
                    child: const ProfileNotificationQuickCard(),
                  ),
                  const SizedBox(height: 24),
                  SectionHeader(
                    title: 'Налаштування',
                    icon: Icons.settings_rounded,
                    padding: const EdgeInsets.fromLTRB(
                      0,
                      NeptunSpacing.xl,
                      0,
                      NeptunSpacing.sectionTitleToContent,
                    ),
                  ),
                  _buildSettingsLinksCard(cs, regionSubtitle),
                  const SizedBox(height: 24),
                  SectionHeader(
                    title: 'Функції PRO',
                    icon: Icons.auto_awesome_rounded,
                    padding: const EdgeInsets.fromLTRB(
                      0,
                      0,
                      0,
                      NeptunSpacing.sectionTitleToContent,
                    ),
                  ),
                  _buildProFeaturesCard(cs),
                  _buildModeratorSection(),
                  const SizedBox(height: 40),
                  Center(
                    child: Opacity(
                      opacity: 0.35,
                      child: Text(
                        '${AppConstants.appName} v${AppConstants.appVersion}',
                        style: GoogleFonts.plusJakartaSans(
                          fontSize: 11,
                          fontWeight: FontWeight.w600,
                          color: NeptunStatus.muted,
                          letterSpacing: 0.5,
                        ),
                      ),
                    ),
                  ),
                ]),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildHeroHeader(ColorScheme cs) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Профіль',
          style: GoogleFonts.plusJakartaSans(
            fontSize: 32,
            fontWeight: FontWeight.w700,
            height: 1.2,
            color: cs.onSurface,
          ),
        ),
        const SizedBox(height: 8),
        Text(
          'Налаштування застосунку та сповіщень',
          style: GoogleFonts.plusJakartaSans(
            fontSize: 16,
            fontWeight: FontWeight.w500,
            color: NeptunStatus.muted,
          ),
        ),
        const SizedBox(height: 12),
        Text(
          '${_nickname.isNotEmpty ? _nickname : 'Гість'} · ${_isPremium ? 'PREMIUM' : 'FREE'}',
          style: GoogleFonts.plusJakartaSans(
            fontSize: 14,
            fontWeight: FontWeight.w600,
            color: cs.onSurface.withValues(alpha: 0.85),
          ),
        ),
      ],
    );
  }

  Widget _buildPremiumHeroContent(ColorScheme cs) {
    return _PremiumHeroCard(
      onTap: () => _push('/premium'),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 56,
                height: 56,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(20),
                  gradient: LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: [
                      NeptunStatus.premium.withValues(alpha: 0.25),
                      NeptunStatus.premium.withValues(alpha: 0.12),
                    ],
                  ),
                  border: Border.all(
                    color: NeptunStatus.premium.withValues(alpha: 0.35),
                  ),
                ),
                child: Icon(
                  Icons.workspace_premium_rounded,
                  color: NeptunStatus.premium,
                  size: 28,
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Flexible(
                          child: Text(
                            'NEPTUN Premium',
                            style: GoogleFonts.plusJakartaSans(
                              fontSize: 19,
                              fontWeight: FontWeight.w700,
                              color: cs.onSurface,
                            ),
                          ),
                        ),
                        const SizedBox(width: 6),
                        Icon(
                          Icons.auto_awesome_rounded,
                          size: 18,
                          color: NeptunStatus.premium,
                        ),
                      ],
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'Розширені можливості',
                      style: GoogleFonts.plusJakartaSans(
                        fontSize: 14,
                        fontWeight: FontWeight.w500,
                        color: NeptunStatus.muted,
                      ),
                    ),
                  ],
                ),
              ),
              Icon(
                Icons.chevron_right_rounded,
                color: NeptunStatus.premium,
                size: 26,
              ),
            ],
          ),
          const SizedBox(height: 18),
          _premiumBullet(cs, 'Детальні карти загроз'),
          _premiumBullet(cs, 'Пріоритетні сповіщення'),
          _premiumBullet(cs, 'Статистика та аналітика'),
        ],
      ),
    );
  }

  Widget _premiumBullet(ColorScheme cs, String text) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.only(top: 6),
            child: Container(
              width: 6,
              height: 6,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: NeptunStatus.premium,
              ),
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              text,
              style: GoogleFonts.plusJakartaSans(
                fontSize: 14,
                fontWeight: FontWeight.w500,
                color: cs.onSurface.withValues(alpha: 0.75),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSettingsLinksCard(ColorScheme cs, String regionSubtitle) {
    return NeptunCard(
      padding: EdgeInsets.zero,
      borderRadius: _kProfileCardRadius,
      backgroundColor: _glassFillColor(context),
      borderColor: _glassBorderColor(context),
      child: Column(
        children: [
          ProfileNavTile(
            icon: Icons.map_rounded,
            label: 'Мій регіон',
            subtitle: regionSubtitle,
            iconAccent: NeptunStatus.accent,
            showDividerBelow: true,
            onTap: () {
              context.go(RoutePaths.radarRegionsView);
              ref.read(regionsSelectionProvider.notifier).reload();
            },
          ),
          ProfileNavTile(
            icon: Icons.tune_rounded,
            label: 'Загальні налаштування',
            subtitle: 'Тема, діагностика, звук тривоги, сон…',
            iconAccent: NeptunStatus.premium,
            showDividerBelow: true,
            onTap: () => _openGeneralSettingsSheet(context),
          ),
          ProfileNavTile(
            icon: Icons.shield_outlined,
            label: 'Конфіденційність та надійність',
            subtitle: 'Звідки ми беремо дані',
            iconAccent: NeptunStatus.safe,
            showDividerBelow: true,
            onTap: () => _push('/trust'),
          ),
          ProfileNavTile(
            icon: Icons.help_outline_rounded,
            label: 'Допомога та підтримка',
            subtitle: 'Відгуки та звернення',
            iconAccent: NeptunStatus.warning,
            showDividerBelow: true,
            onTap: () => _push('/feedback'),
          ),
          ProfileNavTile(
            icon: Icons.health_and_safety_rounded,
            label: 'Центр безпеки',
            subtitle: 'Укриття, медкартка, чекліст',
            iconAccent: NeptunStatus.safe,
            showDividerBelow: true,
            onTap: () => _push('/safety'),
          ),
          ProfileNavTile(
            icon: Icons.telegram,
            label: 'Telegram канал',
            subtitle: 'Офіційні оновлення',
            iconAccent: cs.primary,
            onTap: () => openNeptunTelegramChannel('profile'),
          ),
        ],
      ),
    );
  }

  Widget _buildProFeaturesCard(ColorScheme cs) {
    return NeptunCard(
      padding: EdgeInsets.zero,
      borderRadius: _kProfileCardRadius,
      backgroundColor: _glassFillColor(context),
      borderColor: _glassBorderColor(context),
      child: Column(
        children: [
          ProfileNavTile(
            icon: Icons.history_rounded,
            label: 'Історія',
            subtitle: 'Минулі тривоги',
            iconAccent: NeptunStatus.accent,
            showDividerBelow: true,
            onTap: () => _push('/history'),
          ),
          ProfileNavTile(
            icon: Icons.analytics_rounded,
            label: 'Аналітика',
            subtitle: 'Ваш час у сховищі',
            iconAccent: NeptunStatus.safe,
            showDividerBelow: true,
            onTap: () => _push('/analytics'),
          ),
          ProfileNavTile(
            icon: Icons.whatshot_rounded,
            label: 'Теплова карта',
            subtitle: 'Активність загроз',
            iconAccent: NeptunStatus.warning,
            showDividerBelow: true,
            onTap: () => _push('/heatmap'),
          ),
          ProfileNavTile(
            icon: Icons.palette_rounded,
            label: 'PRO теми',
            subtitle: 'Кастомізація оформлення',
            iconAccent: NeptunStatus.premium,
            onTap: () => _push('/premium'),
          ),
        ],
      ),
    );
  }

  Widget _buildModeratorSection() {
    return StreamBuilder<bool>(
      stream: ModeratorService.instance.stream,
      initialData: ModeratorService.instance.isModerator,
      builder: (context, snap) {
        if (snap.data != true) return const SizedBox.shrink();
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const SizedBox(height: 24),
            SectionHeader(
              title: 'Модерація',
              icon: Icons.admin_panel_settings_rounded,
              padding: const EdgeInsets.fromLTRB(
                0,
                0,
                0,
                NeptunSpacing.sectionTitleToContent,
              ),
            ),
            NeptunCard(
              padding: EdgeInsets.zero,
              borderRadius: _kProfileCardRadius,
              backgroundColor: _glassFillColor(context),
              borderColor: _glassBorderColor(context),
              child: Column(
                children: [
                  ProfileNavTile(
                    icon: Icons.admin_panel_settings_rounded,
                    label: 'Відгуки',
                    iconAccent: NeptunStatus.accent,
                    showDividerBelow: true,
                    onTap: () => _push('/feedback-moderation'),
                  ),
                  ProfileNavTile(
                    icon: Icons.dashboard_rounded,
                    label: 'Адмін панель',
                    iconAccent: NeptunStatus.warning,
                    showDividerBelow: true,
                    onTap: () => _push('/admin'),
                  ),
                  ProfileNavTile(
                    icon: Icons.report_rounded,
                    label: 'Скарги чату',
                    iconAccent: NeptunStatus.alarm,
                    onTap: () => _push('/complaints'),
                  ),
                ],
              ),
            ),
          ],
        );
      },
    );
  }

  void _push(String path) {
    context.push(path);
  }
}

/// Premium tile: gradient, purple glow, soft animated orb (React ProfileView).
class _PremiumHeroCard extends StatefulWidget {
  const _PremiumHeroCard({
    required this.onTap,
    required this.child,
  });

  final VoidCallback onTap;
  final Widget child;

  @override
  State<_PremiumHeroCard> createState() => _PremiumHeroCardState();
}

class _PremiumHeroCardState extends State<_PremiumHeroCard>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 4),
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return AnimatedBuilder(
      animation: _controller,
      builder: (context, _) {
        final t = Curves.easeInOut.transform(_controller.value);
        final scale = 1.0 + 0.2 * t;
        final orbOpacity = (0.25 + 0.15 * t).clamp(0.0, 1.0);
        final gradientEnd = isDark
            ? NeptunSurfaces.s3.withValues(alpha: 0.92)
            : cs.surfaceContainerHighest;
        final gradientColors = [
          Color.alphaBlend(
            NeptunStatus.premium.withValues(alpha: isDark ? 0.15 : 0.1),
            gradientEnd,
          ),
          gradientEnd,
        ];
        final boxShadow = isDark
            ? [
                BoxShadow(
                  color: NeptunStatus.premium.withValues(alpha: 0.15),
                  blurRadius: 36,
                  offset: const Offset(0, 16),
                ),
                BoxShadow(
                  color: Colors.black.withValues(alpha: 0.18),
                  blurRadius: 20,
                  offset: const Offset(0, 8),
                ),
              ]
            : [
                BoxShadow(
                  color: NeptunStatus.premium.withValues(alpha: 0.16),
                  blurRadius: 22,
                  offset: const Offset(0, 10),
                ),
                BoxShadow(
                  color: cs.primary.withValues(alpha: 0.06),
                  blurRadius: 14,
                  offset: const Offset(0, 5),
                ),
              ];
        return Material(
          color: Colors.transparent,
          child: InkWell(
            onTap: widget.onTap,
            borderRadius: BorderRadius.circular(_kProfileCardRadius),
            child: Ink(
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(_kProfileCardRadius),
                gradient: LinearGradient(
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                  colors: gradientColors,
                ),
                border: Border.all(
                  color: NeptunStatus.premium.withValues(alpha: isDark ? 0.3 : 0.28),
                ),
                boxShadow: boxShadow,
              ),
              child: ClipRRect(
                borderRadius: BorderRadius.circular(_kProfileCardRadius),
                child: Stack(
                  clipBehavior: Clip.hardEdge,
                  children: [
                    Positioned(
                      top: -28,
                      right: -28,
                      child: Transform.scale(
                        scale: scale,
                        child: Opacity(
                          opacity: orbOpacity,
                          child: Container(
                            width: 128,
                            height: 128,
                            decoration: BoxDecoration(
                              shape: BoxShape.circle,
                              gradient: RadialGradient(
                                colors: [
                                  NeptunStatus.premium.withValues(alpha: 0.55),
                                  Colors.transparent,
                                ],
                                stops: const [0.0, 0.72],
                              ),
                            ),
                          ),
                        ),
                      ),
                    ),
                    Padding(
                      padding: const EdgeInsets.all(18),
                      child: DefaultTextStyle.merge(
                        style: TextStyle(color: cs.onSurface),
                        child: widget.child,
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
  }
}
