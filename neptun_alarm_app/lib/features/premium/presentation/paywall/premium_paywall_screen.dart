import 'dart:ui' show ImageFilter;

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:neptun_alarm_app/config/app_constants.dart';
import 'package:neptun_alarm_app/core/pro/pro_features.dart';
import 'package:neptun_alarm_app/core/widgets/neptun_shimmer.dart';
import 'package:neptun_alarm_app/core/widgets/neptun_shell_modal.dart';
import 'package:neptun_alarm_app/features/premium/presentation/paywall/premium_paywall_style.dart';
import 'package:neptun_alarm_app/features/premium/presentation/providers/premium_provider.dart';
import 'package:neptun_alarm_app/services/pro_customization_service.dart';

class PremiumPaywallScreen extends ConsumerStatefulWidget {
  const PremiumPaywallScreen({super.key});

  @override
  ConsumerState<PremiumPaywallScreen> createState() =>
      _PremiumPaywallScreenState();
}

class _PremiumPaywallScreenState extends ConsumerState<PremiumPaywallScreen>
    with SingleTickerProviderStateMixin {
  late AnimationController _entranceController;
  ProviderSubscription<String?>? _premiumErrorSub;

  static const double _kH = 22;
  static const double _kPanelRadius = 22;

  void _refreshUi() => setState(() {});

  @override
  void initState() {
    super.initState();
    _entranceController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 880),
    );
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (mounted) _entranceController.forward();
    });

    _premiumErrorSub = ref.listenManual<String?>(
      premiumProvider.select((s) => s.error),
      (previous, next) {
        if (next == null || !mounted) return;
        final messenger = ScaffoldMessenger.maybeOf(context);
        if (messenger == null) return;
        messenger.showSnackBar(
          SnackBar(
            content: Text(next),
            behavior: SnackBarBehavior.floating,
            backgroundColor: Theme.of(context).colorScheme.error,
          ),
        );
      },
    );
  }

  @override
  void dispose() {
    _premiumErrorSub?.close();
    _entranceController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(premiumProvider);
    final style = PremiumPaywallStyle.dark;

    if (state.isLoading && !state.isPurchasing) {
      return _PaywallLoading(style: style);
    }

    return Scaffold(
      backgroundColor: Colors.transparent,
      body: Stack(
        fit: StackFit.expand,
        children: [
          _PaywallBackground(style: style),
          Positioned.fill(
            child: state.showThankYou
                ? _ThankYouScreen(style: style)
                : (state.isPremium
                    ? _buildMemberScaffold(state, style)
                    : _buildPaywallScaffold(state, style)),
          ),
          if (!state.isPremium && !state.showThankYou)
            Positioned(
              left: 0,
              right: 0,
              bottom: 0,
              child: _StickyCtaBar(
                style: style,
                state: state,
                price: state.productPrice ?? AppConstants.premiumDisplayPrice,
                onBuy: () => ref.read(premiumProvider.notifier).buyPremium(),
              ),
            ),
        ],
      ),
    );
  }

  String _displayPrice(PremiumState state) =>
      state.productPrice ?? AppConstants.premiumDisplayPrice;

  Widget _buildPaywallScaffold(PremiumState state, PremiumPaywallStyle style) {
    return Column(
      children: [
        Expanded(
          child: CustomScrollView(
            physics: const BouncingScrollPhysics(
              parent: AlwaysScrollableScrollPhysics(),
            ),
            slivers: [
              _buildSliverTopBar(state, style),
              SliverPadding(
                padding: const EdgeInsets.fromLTRB(_kH, 8, _kH, 0),
                sliver: SliverList(
                  delegate: SliverChildListDelegate([
                    _HeroBlock(
                      style: style,
                      isPremium: state.isPremium,
                    ),
                    const SizedBox(height: 32),
                    _PremiumPriceBlock(
                      style: style,
                      price: _displayPrice(state),
                    ),
                    const SizedBox(height: 24),
                    _SupportText(style: style),
                    const SizedBox(height: 32),
                    Text(
                      'ЩО ВХОДИТЬ',
                      style: GoogleFonts.plusJakartaSans(
                        fontSize: 13,
                        fontWeight: FontWeight.w700,
                        letterSpacing: 2,
                        color: style.textTertiary,
                      ),
                    ),
                    const SizedBox(height: 14),
                    FadeTransition(
                      opacity: CurvedAnimation(
                        parent: _entranceController,
                        curve: const Interval(
                          0.15,
                          1,
                          curve: Curves.easeOutCubic,
                        ),
                      ),
                      child: SlideTransition(
                        position: Tween<Offset>(
                          begin: const Offset(0, 0.04),
                          end: Offset.zero,
                        ).animate(
                          CurvedAnimation(
                            parent: _entranceController,
                            curve: const Interval(
                              0.15,
                              1,
                              curve: Curves.easeOutCubic,
                            ),
                          ),
                        ),
                        child: _FeaturesPanel(
                          style: style,
                          entrance: _entranceController,
                        ),
                      ),
                    ),
                    const SizedBox(height: 20),
                    Text(
                      'Оплата через Apple або Google.\nПоживний доступ без жодних прихованих платежів.',
                      textAlign: TextAlign.center,
                      style: GoogleFonts.plusJakartaSans(
                        fontSize: 12,
                        height: 1.55,
                        color: style.textTertiary,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                    const SizedBox(height: 48),
                    const SizedBox(height: 120),
                  ]),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildMemberScaffold(PremiumState state, PremiumPaywallStyle style) {
    return CustomScrollView(
      physics: const BouncingScrollPhysics(),
      slivers: [
        _buildSliverTopBar(state, style),
        SliverPadding(
          padding: const EdgeInsets.fromLTRB(_kH, 8, _kH, 40),
          sliver: SliverList(
            delegate: SliverChildListDelegate([
              _HeroBlock(
                style: style,
                isPremium: true,
              ),
              const SizedBox(height: 32),
              _MemberSettings(
                style: style,
                onUiChanged: _refreshUi,
                onThemeTap: showThemePickerSheet,
              ),
            ]),
          ),
        ),
      ],
    );
  }

  Widget _buildSliverTopBar(PremiumState state, PremiumPaywallStyle style) {
    return SliverAppBar(
      pinned: false,
      floating: true,
      snap: true,
      backgroundColor: Colors.transparent,
      elevation: 0,
      automaticallyImplyLeading: false,
      toolbarHeight: 52,
      titleSpacing: 0,
      title: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 8),
        child: Row(
          children: [
            _ChromeIconButton(
              style: style,
              icon: Icons.close_rounded,
              onPressed: () => Navigator.of(context).maybePop(),
            ),
            const Spacer(),
            if (!state.isPremium)
              TextButton(
                onPressed: () =>
                    ref.read(premiumProvider.notifier).restorePurchases(),
                child: Text(
                  'Відновити',
                  style: GoogleFonts.plusJakartaSans(
                    color: style.textSecondary,
                    fontWeight: FontWeight.w600,
                    fontSize: 15,
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }

  void showThemePickerSheet() {
    final proService = ref.read(proCustomizationProvider);
    final style = PremiumPaywallStyle.of(context);
    final sheetBg = style.panel;
    final isDark = Theme.of(context).brightness == Brightness.dark;

    NeptunShellModal.showBottomSheet(
      context: context,
      backgroundColor: isDark ? const Color(0xFF121722) : sheetBg,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(28)),
      ),
      builder: (ctx) {
        return Padding(
          padding: const EdgeInsets.fromLTRB(24, 20, 24, 32),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                'Тема чату',
                style: GoogleFonts.plusJakartaSans(
                  color: style.textPrimary,
                  fontSize: 20,
                  fontWeight: FontWeight.w800,
                ),
              ),
              const SizedBox(height: 22),
              Wrap(
                spacing: 16,
                runSpacing: 16,
                alignment: WrapAlignment.center,
                children: ChatTheme.all
                    .map(
                      (t) => GestureDetector(
                        onTap: () async {
                          final nav = Navigator.of(ctx);
                          await proService.setChatTheme(t.id);
                          if (mounted) nav.pop();
                          if (mounted) setState(() {});
                        },
                        child: Column(
                          children: [
                            Container(
                              width: 56,
                              height: 56,
                              decoration: BoxDecoration(
                                color: t.bubbleColor == Colors.transparent
                                    ? style.textTertiary
                                    : t.bubbleColor,
                                shape: BoxShape.circle,
                                border: proService.selectedChatThemeId == t.id
                                    ? Border.all(
                                        color: style.accent,
                                        width: 3,
                                      )
                                    : null,
                              ),
                            ),
                            const SizedBox(height: 8),
                            Text(
                              t.name,
                              style: GoogleFonts.plusJakartaSans(
                                color: style.textSecondary,
                                fontSize: 12,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ],
                        ),
                      ),
                    )
                    .toList(),
              ),
            ],
          ),
        );
      },
    );
  }
}

// —— Background ——————————————————————————————————————————————————————

class _PaywallBackground extends StatelessWidget {
  const _PaywallBackground({required this.style});

  final PremiumPaywallStyle style;

  @override
  Widget build(BuildContext context) {
    return Stack(
      fit: StackFit.expand,
      children: [
        DecoratedBox(
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topCenter,
              end: Alignment.bottomCenter,
              colors: [
                style.backgroundTop,
                style.backgroundMid,
                style.backgroundBottom,
              ],
            ),
          ),
        ),
        Positioned(
          top: -120,
          left: 0,
          right: 0,
          child: IgnorePointer(
            child: Container(
              height: 360,
              decoration: BoxDecoration(
                gradient: RadialGradient(
                  center: Alignment.topCenter,
                  radius: 0.95,
                  colors: [style.auroraGold, Colors.transparent],
                  stops: const [0.0, 0.65],
                ),
              ),
            ),
          ),
        ),
        Positioned(
          bottom: -80,
          right: -60,
          child: IgnorePointer(
            child: Container(
              width: 280,
              height: 280,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                gradient: RadialGradient(
                  colors: [style.auroraCool, Colors.transparent],
                  stops: const [0.0, 0.7],
                ),
              ),
            ),
          ),
        ),
      ],
    );
  }
}

class _PaywallLoading extends StatelessWidget {
  const _PaywallLoading({required this.style});

  final PremiumPaywallStyle style;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: style.backgroundTop,
      body: Stack(
        fit: StackFit.expand,
        children: [
          _PaywallBackground(style: style),
          SafeArea(
            child: Padding(
              padding: const EdgeInsets.all(_PremiumPaywallScreenState._kH),
              child: Column(
                children: [
                  const SizedBox(height: 40),
                  NeptunShimmer(
                    width: 72,
                    height: 72,
                    borderRadius: 36,
                    opacity: 0.45,
                  ),
                  const SizedBox(height: 28),
                  NeptunShimmer(
                    width: 220,
                    height: 28,
                    borderRadius: 8,
                    opacity: 0.45,
                  ),
                  const SizedBox(height: 14),
                  NeptunShimmer(
                    width: 160,
                    height: 16,
                    borderRadius: 8,
                    opacity: 0.45,
                  ),
                  const SizedBox(height: 40),
                  Expanded(
                    child: NeptunShimmer(
                      width: double.infinity,
                      height: double.infinity,
                      borderRadius: _PremiumPaywallScreenState._kPanelRadius,
                      opacity: 0.4,
                    ),
                  ),
                  const SizedBox(height: 100),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// —— Hero ——————————————————————————————————————————————————————————

class _HeroBlock extends StatelessWidget {
  const _HeroBlock({
    required this.style,
    required this.isPremium,
  });

  final PremiumPaywallStyle style;
  final bool isPremium;

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Container(
          width: 88,
          height: 88,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            gradient: LinearGradient(
              colors: [
                style.accent.withValues(alpha: 0.35),
                style.accentDeep.withValues(alpha: 0.15),
              ],
            ),
            boxShadow: [
              BoxShadow(
                color: style.accent.withValues(alpha: 0.22),
                blurRadius: 32,
                spreadRadius: 0,
              ),
            ],
          ),
          padding: const EdgeInsets.all(3),
          child: DecoratedBox(
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: style.backgroundMid.withValues(alpha: 0.92),
            ),
            child: Icon(
              Icons.auto_awesome_rounded,
              size: 38,
              color: style.accent,
            ),
          ),
        ),
        const SizedBox(height: 26),
        Text(
          isPremium ? 'Ви з PRO' : 'Dron Alerts PRO',
          textAlign: TextAlign.center,
          style: GoogleFonts.plusJakartaSans(
            fontSize: 34,
            fontWeight: FontWeight.w800,
            height: 1.08,
            letterSpacing: -0.8,
            color: style.textPrimary,
          ),
        ),
        const SizedBox(height: 12),
        Text(
          isPremium
              ? 'Дякуємо за підтримку Dron Alerts 💙💛'
              : 'Розширені функції та підтримка розвитку проєкту',
          textAlign: TextAlign.center,
          style: GoogleFonts.plusJakartaSans(
            fontSize: 17,
            fontWeight: FontWeight.w500,
            height: 1.45,
            color: style.textSecondary,
          ),
        ),
      ],
    );
  }
}

class _PremiumPriceBlock extends StatelessWidget {
  const _PremiumPriceBlock({required this.style, required this.price});

  final PremiumPaywallStyle style;
  final String price;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(24),
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            style.accent.withValues(alpha: 0.12),
            style.accentDeep.withValues(alpha: 0.05),
          ],
        ),
        border: Border.all(
          color: style.accent.withValues(alpha: 0.3),
          width: 1.5,
        ),
        boxShadow: [
          BoxShadow(
            color: style.accent.withValues(alpha: 0.08),
            blurRadius: 40,
            spreadRadius: 0,
            offset: const Offset(0, 10),
          ),
        ],
      ),
      padding: const EdgeInsets.symmetric(vertical: 32, horizontal: 24),
      child: Column(
        children: [
          Text(
            price,
            style: GoogleFonts.plusJakartaSans(
              fontSize: 44,
              fontWeight: FontWeight.w800,
              letterSpacing: -1.5,
              color: style.accent,
              height: 1,
              shadows: [
                Shadow(
                  color: style.accent.withValues(alpha: 0.3),
                  blurRadius: 20,
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              _PriceLabel(style: style, text: 'Одноразова покупка'),
              const _PriceDot(),
              _PriceLabel(style: style, text: 'Без підписок'),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            'PRO доступ назавжди',
            style: GoogleFonts.plusJakartaSans(
              fontSize: 14,
              fontWeight: FontWeight.w700,
              color: style.accent.withValues(alpha: 0.9),
              letterSpacing: 0.5,
            ),
          ),
        ],
      ),
    );
  }
}

class _PriceLabel extends StatelessWidget {
  const _PriceLabel({required this.style, required this.text});
  final PremiumPaywallStyle style;
  final String text;

  @override
  Widget build(BuildContext context) {
    return Text(
      text,
      style: GoogleFonts.plusJakartaSans(
        fontSize: 13,
        fontWeight: FontWeight.w600,
        color: style.textSecondary,
      ),
    );
  }
}

class _PriceDot extends StatelessWidget {
  const _PriceDot();
  @override
  Widget build(BuildContext context) {
    return Container(
      width: 4,
      height: 4,
      margin: const EdgeInsets.symmetric(horizontal: 10),
      decoration: const BoxDecoration(
        color: Colors.white24,
        shape: BoxShape.circle,
      ),
    );
  }
}

class _SupportText extends StatelessWidget {
  const _SupportText({required this.style});
  final PremiumPaywallStyle style;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Text(
        'Ваш PRO допомагає підтримувати сервери та розвиток українського застосунку Dron Alerts 💙💛',
        textAlign: TextAlign.center,
        style: GoogleFonts.plusJakartaSans(
          fontSize: 14,
          fontWeight: FontWeight.w500,
          height: 1.5,
          color: style.textSecondary.withValues(alpha: 0.9),
        ),
      ),
    );
  }
}

// —— Features panel ——————————————————————————————————————————————

class _FeaturesPanel extends StatelessWidget {
  const _FeaturesPanel({
    required this.style,
    required this.entrance,
  });

  final PremiumPaywallStyle style;
  final Animation<double> entrance;

  static const _items = <(ProFeature?, IconData, String, String, bool)>[
    (null, Icons.dns_rounded, 'Підтримка серверів', 'Ваш внесок оплачує стабільну роботу інфраструктури', true),
    (ProFeature.trajectories, Icons.auto_graph_rounded, 'AI-прогноз напрямку', 'Візуалізація траєкторій та прогноз руху загроз', false),
    (ProFeature.extendedRadar, Icons.radar_rounded, 'Розширена карта', 'Повний радар із детальним відображенням цілей', false),
    (ProFeature.priorityNotifications, Icons.notifications_active_rounded, 'Ранні сповіщення', 'Пріоритетний канал доставки миттєвих пушів', false),
    (ProFeature.customAlarmSounds, Icons.volume_up_rounded, 'Кастомні звуки', 'Унікальні сигнали для різних типів загроз', false),
    (ProFeature.alarmHistory, Icons.history_rounded, 'Історія руху', 'Журнал переміщення ворожих об’єктів', false),
    (ProFeature.widgetCustomization, Icons.widgets_rounded, 'Віджети', 'Розширені налаштування віджетів на головному екрані', false),
    (null, Icons.favorite_rounded, 'Розвиток Dron Alerts', 'Допомога в створенні нових функцій для безпеки', false),
  ];

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(_PremiumPaywallScreenState._kPanelRadius),
        color: style.panel,
        border: Border.all(color: style.panelBorder),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.12),
            blurRadius: 40,
            offset: const Offset(0, 18),
          ),
        ],
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(_PremiumPaywallScreenState._kPanelRadius),
        child: Column(
          children: [
            for (var i = 0; i < _items.length; i++) ...[
              _FeatureRow(
                icon: _items[i].$2,
                feature: _items[i].$1,
                name: _items[i].$3,
                desc: _items[i].$4,
                isNew: _items[i].$5,
                style: style,
                entrance: entrance,
                index: i,
                total: _items.length,
              ),
              if (i < _items.length - 1)
                Divider(height: 1, thickness: 1, color: style.hairline),
            ],
          ],
        ),
      ),
    );
  }
}

class _FeatureRow extends StatelessWidget {
  const _FeatureRow({
    required this.icon,
    this.feature,
    required this.name,
    required this.desc,
    required this.isNew,
    required this.style,
    required this.entrance,
    required this.index,
    required this.total,
  });

  final IconData icon;
  final ProFeature? feature;
  final String name;
  final String desc;
  final bool isNew;
  final PremiumPaywallStyle style;
  final Animation<double> entrance;
  final int index;
  final int total;

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: entrance,
      builder: (context, _) {
        final t = CurvedAnimation(
          parent: entrance,
          curve: Interval(
            0.1 + 0.55 * (index / total),
            1,
            curve: Curves.easeOutCubic,
          ),
        ).value;
        return Opacity(
          opacity: t,
          child: Transform.translate(
            offset: Offset(0, 6 * (1 - t)),
            child: Padding(
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 16),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Icon(icon, size: 22, color: style.accent.withValues(alpha: 0.95)),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Text(
                              name,
                              style: GoogleFonts.plusJakartaSans(
                                fontSize: 15,
                                fontWeight: FontWeight.w700,
                                color: style.textPrimary,
                                height: 1.2,
                              ),
                            ),
                            if (isNew)
                              Padding(
                                padding: const EdgeInsets.only(left: 8),
                                child: Container(
                                  padding: const EdgeInsets.symmetric(
                                    horizontal: 6,
                                    vertical: 2,
                                  ),
                                  decoration: BoxDecoration(
                                    color: style.accent.withValues(alpha: 0.18),
                                    borderRadius: BorderRadius.circular(4),
                                  ),
                                  child: Text(
                                    'NEW',
                                    style: GoogleFonts.plusJakartaSans(
                                      fontSize: 9,
                                      fontWeight: FontWeight.w800,
                                      color: style.accent,
                                      letterSpacing: 0.8,
                                    ),
                                  ),
                                ),
                              ),
                          ],
                        ),
                        const SizedBox(height: 4),
                        Text(
                          desc,
                          style: GoogleFonts.plusJakartaSans(
                            fontSize: 13,
                            height: 1.4,
                            color: style.textSecondary,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
          ),
        );
      },
    );
  }
}

// —— Sticky CTA ————————————————————————————————————————————————

class _StickyCtaBar extends StatelessWidget {
  const _StickyCtaBar({
    required this.style,
    required this.state,
    required this.price,
    required this.onBuy,
  });

  final PremiumPaywallStyle style;
  final PremiumState state;
  final String price;
  final VoidCallback onBuy;

  @override
  Widget build(BuildContext context) {
    return ClipRect(
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: 20, sigmaY: 20),
        child: DecoratedBox(
          decoration: BoxDecoration(
            color: style.stickyScrim,
            border: Border(
              top: BorderSide(color: style.hairline),
            ),
          ),
          child: SafeArea(
            top: false,
            minimum: const EdgeInsets.fromLTRB(
              _PremiumPaywallScreenState._kH,
              12,
              _PremiumPaywallScreenState._kH,
              12,
            ),
            child: Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Text(
                        'Підтримка проєкту',
                        style: GoogleFonts.plusJakartaSans(
                          fontSize: 11,
                          fontWeight: FontWeight.w700,
                          letterSpacing: 0.6,
                          color: style.textTertiary,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        'PRO назавжди',
                        style: GoogleFonts.plusJakartaSans(
                          fontSize: 18,
                          fontWeight: FontWeight.w800,
                          color: style.textPrimary,
                          height: 1,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 12),
                Material(
                  color: Colors.transparent,
                  child: InkWell(
                    onTap: state.isPurchasing ? null : onBuy,
                    borderRadius: BorderRadius.circular(16),
                    child: Ink(
                      decoration: BoxDecoration(
                        gradient: style.ctaGradient,
                        borderRadius: BorderRadius.circular(16),
                        boxShadow: state.isPurchasing
                            ? []
                            : [
                                BoxShadow(
                                  color: style.accent.withValues(alpha: 0.28),
                                  blurRadius: 16,
                                  offset: const Offset(0, 6),
                                ),
                              ],
                      ),
                      child: ConstrainedBox(
                        constraints: const BoxConstraints(
                          minWidth: 148,
                          minHeight: 52,
                        ),
                        child: Center(
                          child: state.isPurchasing
                              ? SizedBox(
                                  width: 22,
                                  height: 22,
                                  child: CircularProgressIndicator(
                                    strokeWidth: 2.5,
                                    color: style.ctaText,
                                  ),
                                )
                              : Padding(
                                  padding: const EdgeInsets.symmetric(
                                    horizontal: 20,
                                  ),
                                  child: Text(
                                    'Підтримати',
                                    style: GoogleFonts.plusJakartaSans(
                                      color: style.ctaText,
                                      fontWeight: FontWeight.w800,
                                      fontSize: 16,
                                    ),
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
        ),
      ),
    );
  }
}

// —— Chrome ———————————————————————————————————————————————————

class _ChromeIconButton extends StatelessWidget {
  const _ChromeIconButton({
    required this.style,
    required this.icon,
    required this.onPressed,
  });

  final PremiumPaywallStyle style;
  final IconData icon;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) {
    return Material(
      color: style.panel,
      shape: const CircleBorder(),
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: onPressed,
        child: Padding(
          padding: const EdgeInsets.all(10),
          child: Icon(icon, color: style.chromeIcon, size: 22),
        ),
      ),
    );
  }
}

// —— Member settings ——————————————————————————————————————————

class _MemberSettings extends ConsumerWidget {
  const _MemberSettings({
    required this.style,
    required this.onUiChanged,
    required this.onThemeTap,
  });

  final PremiumPaywallStyle style;
  final VoidCallback onUiChanged;
  final VoidCallback onThemeTap;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final proService = ref.watch(proCustomizationProvider);

    return DecoratedBox(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(_PremiumPaywallScreenState._kPanelRadius),
        color: style.panel,
        border: Border.all(color: style.panelBorder),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.08),
            blurRadius: 28,
            offset: const Offset(0, 14),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          _MemberSectionLabel(text: 'Оформлення', style: style),
          _MemberTile(
            style: style,
            icon: Icons.palette_rounded,
            title: 'Тема чату',
            subtitle: proService.selectedChatTheme.name,
            onTap: onThemeTap,
          ),
          Divider(height: 1, color: style.hairline),
          _MemberTile(
            style: style,
            icon: Icons.motion_photos_on_rounded,
            title: 'Анімована аватарка',
            subtitle: proService.isAnimatedAvatarEnabled
                ? 'Увімкнено в чаті'
                : 'Вимкнено',
            trailing: Switch(
              value: proService.isAnimatedAvatarEnabled,
              activeThumbColor: style.accent,
              activeTrackColor: style.accent.withValues(alpha: 0.35),
              onChanged: (v) async {
                await proService.setAnimatedAvatar(v);
                onUiChanged();
              },
            ),
          ),
          Divider(height: 1, color: style.hairline),
          _MemberSectionLabel(text: 'Функції', style: style),
          _MemberTile(
            style: style,
            icon: Icons.history_rounded,
            title: 'Історія тривог',
            subtitle: 'Журнал загроз',
            onTap: () => context.push('/history'),
          ),
          Divider(height: 1, color: style.hairline),
          _MemberTile(
            style: style,
            icon: Icons.analytics_rounded,
            title: 'Аналітика',
            subtitle: 'Час під тривогою',
            onTap: () => context.push('/analytics'),
          ),
          Divider(height: 1, color: style.hairline),
          _MemberTile(
            style: style,
            icon: Icons.whatshot_rounded,
            title: 'Теплова карта',
            subtitle: 'Активність по регіонах',
            onTap: () => context.push('/heatmap'),
          ),
          Divider(height: 1, color: style.hairline),
          _MemberTile(
            style: style,
            icon: Icons.bedtime_rounded,
            title: 'Режим сну',
            subtitle: 'Налаштування сповіщень вночі',
            onTap: () => context.go('/profile'),
          ),
          Divider(height: 1, color: style.hairline),
          _MemberTile(
            style: style,
            icon: Icons.volume_up_rounded,
            title: 'Звук тривоги',
            subtitle: 'У профілі',
            onTap: () => context.go('/profile'),
          ),
        ],
      ),
    );
  }
}

class _MemberSectionLabel extends StatelessWidget {
  const _MemberSectionLabel({required this.text, required this.style});

  final String text;
  final PremiumPaywallStyle style;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(18, 18, 18, 6),
      child: Text(
        text.toUpperCase(),
        style: GoogleFonts.plusJakartaSans(
          fontSize: 11,
          fontWeight: FontWeight.w800,
          letterSpacing: 1.4,
          color: style.textTertiary,
        ),
      ),
    );
  }
}

class _MemberTile extends StatelessWidget {
  const _MemberTile({
    required this.style,
    required this.icon,
    required this.title,
    required this.subtitle,
    this.onTap,
    this.trailing,
  });

  final PremiumPaywallStyle style;
  final IconData icon;
  final String title;
  final String subtitle;
  final VoidCallback? onTap;
  final Widget? trailing;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: trailing != null ? null : onTap,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        child: Row(
          children: [
            Icon(icon, color: style.accent, size: 22),
            const SizedBox(width: 14),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: GoogleFonts.plusJakartaSans(
                      fontSize: 15,
                      fontWeight: FontWeight.w700,
                      color: style.textPrimary,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    subtitle,
                    style: GoogleFonts.plusJakartaSans(
                      fontSize: 12,
                      color: style.textSecondary,
                      height: 1.3,
                    ),
                  ),
                ],
              ),
            ),
            trailing ??
                Icon(
                  Icons.chevron_right_rounded,
                  color: style.textTertiary,
                  size: 22,
                ),
          ],
        ),
      ),
    );
  }
}
class _ThankYouScreen extends StatelessWidget {
  const _ThankYouScreen({required this.style});
  final PremiumPaywallStyle style;

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        Container(
          width: 120,
          height: 120,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: style.accent.withValues(alpha: 0.1),
            border: Border.all(color: style.accent.withValues(alpha: 0.3)),
          ),
          child: Icon(
            Icons.favorite_rounded,
            size: 64,
            color: style.accent,
          ),
        ),
        const SizedBox(height: 40),
        Text(
          'Дякуємо за підтримку\nDron Alerts 💙💛',
          textAlign: TextAlign.center,
          style: GoogleFonts.plusJakartaSans(
            fontSize: 28,
            fontWeight: FontWeight.w800,
            color: style.textPrimary,
            height: 1.2,
          ),
        ),
        const SizedBox(height: 20),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 40),
          child: Text(
            'Ваш внесок допомагає нам розвивати застосунок та підтримувати сервери для безпеки українців.',
            textAlign: TextAlign.center,
            style: GoogleFonts.plusJakartaSans(
              fontSize: 16,
              fontWeight: FontWeight.w500,
              color: style.textSecondary,
              height: 1.5,
            ),
          ),
        ),
        const SizedBox(height: 48),
        SizedBox(
          width: 200,
          child: FilledButton(
            onPressed: () => Navigator.of(context).pop(),
            style: FilledButton.styleFrom(
              backgroundColor: style.accent,
              foregroundColor: style.ctaText,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(16),
              ),
              padding: const EdgeInsets.symmetric(vertical: 16),
            ),
            child: Text(
              'Почати роботу',
              style: GoogleFonts.plusJakartaSans(
                fontWeight: FontWeight.w800,
                fontSize: 16,
              ),
            ),
          ),
        ),
      ],
    );
  }
}
