import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:url_launcher/url_launcher.dart';
import '../../core/di/service_locator.dart';
import '../../services/moderator_service.dart';
import '../../services/purchase_service.dart';
import '../../config/app_constants.dart';
import '../../design/design_exports.dart';
import '../../widgets/profile_nav_tile.dart';
import '../../widgets/settings_section.dart';

/// Profile tab -- replaces Menu tab with richer profile + navigation hub.
class ProfileTab extends StatefulWidget {
  const ProfileTab({super.key});

  @override
  State<ProfileTab> createState() => _ProfileTabState();
}

class _ProfileTabState extends State<ProfileTab>
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

  @override
  Widget build(BuildContext context) {
    super.build(context);
    final cs = Theme.of(context).colorScheme;
    final topInset = MediaQuery.of(context).padding.top + 52 + NeptunSpacing.lg;

    return ListView(
      padding: EdgeInsets.fromLTRB(
        NeptunSpacing.lg,
        topInset,
        NeptunSpacing.lg,
        NeptunSpacing.xxxl,
      ),
      children: [
        // Profile card — tactical raised surface
        _buildProfileCard(cs),
        const SizedBox(height: NeptunSpacing.xl),

        // PRO banner — glow accent
        if (!_isPremium) ...[
          _buildPremiumBanner(cs),
          const SizedBox(height: NeptunSpacing.xl),
        ],

        // Settings section
        SectionHeader(title: 'Налаштування', icon: Icons.settings_rounded),
        const SizedBox(height: NeptunSpacing.sm),
        const SettingsSection(),
        const SizedBox(height: NeptunSpacing.xl),

        // Features section
        SectionHeader(title: 'Функції', icon: Icons.grid_view_rounded),
        const SizedBox(height: NeptunSpacing.sm),
        TacticalSurface(
          style: TacticalSurfaceStyle.flat,
          padding: EdgeInsets.zero,
          margin: const EdgeInsets.only(bottom: NeptunSpacing.md),
          child: Column(
            children: [
              ProfileNavTile(
          icon: Icons.location_on_rounded,
          label: 'Регіони сповіщень',
          subtitle: 'Обрати область чи район для тривог',
          onTap: () => context.go('/regions'),
        ),
        ProfileNavTile(
          icon: Icons.history_rounded,
          label: 'Історія тривог',
          subtitle: 'Журнал минулих загроз',
          badge: _isPremium ? null : 'PRO',
          onTap: () => _push('/history'),
        ),
        ProfileNavTile(
          icon: Icons.analytics_rounded,
          label: 'Аналітика',
          subtitle: 'Персональна статистика',
          badge: _isPremium ? null : 'PRO',
          onTap: () => _push('/analytics'),
        ),
        ProfileNavTile(
          icon: Icons.whatshot_rounded,
          label: 'Теплова карта',
          subtitle: 'Тривоги по регіонах',
          badge: _isPremium ? null : 'PRO',
          onTap: () => _push('/heatmap'),
        ),
            ],
          ),
        ),

        // Trust & info
        SectionHeader(title: 'Інформація', icon: Icons.info_outline_rounded),
        const SizedBox(height: NeptunSpacing.sm),
        TacticalSurface(
          style: TacticalSurfaceStyle.flat,
          padding: EdgeInsets.zero,
          margin: const EdgeInsets.only(bottom: NeptunSpacing.md),
          child: Column(
            children: [
              ProfileNavTile(
          icon: Icons.verified_user_rounded,
          label: 'Надійність',
          subtitle: 'Статус серверів, джерела даних',
          onTap: () => _push('/trust'),
        ),
        ProfileNavTile(
          icon: Icons.feedback_rounded,
          label: 'Зворотній зв\'язок',
          subtitle: 'Баги, пропозиції, запити',
          onTap: () => _push('/feedback'),
        ),
        ProfileNavTile(
          icon: Icons.privacy_tip_rounded,
          label: 'Політика конфіденційності',
          subtitle: 'Як ми зберігаємо та використовуємо дані',
          onTap: () => launchUrl(
            Uri.parse('https://neptun.in.ua/privacy'),
            mode: LaunchMode.externalApplication,
          ),
        ),
        ProfileNavTile(
          icon: Icons.description_rounded,
          label: 'Умови використання',
          onTap: () => launchUrl(
            Uri.parse('https://neptun.in.ua/terms'),
            mode: LaunchMode.externalApplication,
          ),
        ),
        ProfileNavTile(
          icon: Icons.send_rounded,
          label: 'Telegram канал',
          onTap: () => launchUrl(
            Uri.parse('https://t.me/+Q0PcuV4OkuxmYjVi'),
            mode: LaunchMode.externalApplication,
          ),
        ),
        ProfileNavTile(
          icon: Icons.language_rounded,
          label: 'Вебсайт',
          onTap: () => launchUrl(
            Uri.parse('https://neptun.in.ua'),
            mode: LaunchMode.externalApplication,
          ),
        ),
            ],
          ),
        ),

        // Moderator section (visible only when logged in as moderator)
        StreamBuilder<bool>(
          stream: ModeratorService.instance.stream,
          initialData: ModeratorService.instance.isModerator,
          builder: (context, snap) {
            if (snap.data != true) return const SizedBox.shrink();
            return Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const SizedBox(height: NeptunSpacing.xl),
                SectionHeader(title: 'Модерація', icon: Icons.admin_panel_settings_rounded),
                const SizedBox(height: NeptunSpacing.sm),
                TacticalSurface(
                  style: TacticalSurfaceStyle.flat,
                  padding: EdgeInsets.zero,
                  margin: const EdgeInsets.only(bottom: NeptunSpacing.md),
                  child: Column(
                    children: [
                      ProfileNavTile(
                  icon: Icons.admin_panel_settings_rounded,
                  label: 'Модерація відгуків',
                  subtitle: 'Перегляд та модерація відгуків',
                  onTap: () => _push('/feedback-moderation'),
                ),
                ProfileNavTile(
                  icon: Icons.dashboard_rounded,
                  label: 'Адмін панель',
                  subtitle: 'Керування системою',
                  onTap: () => _push('/admin'),
                ),
                ProfileNavTile(
                  icon: Icons.report_rounded,
                  label: 'Скарги чату',
                  subtitle: 'Перегляд та обробка скарг',
                  onTap: () => _push('/complaints'),
                ),
                    ],
                  ),
                ),
              ],
            );
          },
        ),

        const SizedBox(height: NeptunSpacing.xxl),

        // Version
        Center(
          child: Text(
            '${AppConstants.appName} v${AppConstants.appVersion}',
            style: GoogleFonts.plusJakartaSans(
              fontSize: 12,
              color: cs.onSurface.withValues(alpha: 0.25),
            ),
          ),
        ),
      ],
    );
  }

  void _push(String path) {
    context.push(path);
  }

  Widget _buildProfileCard(ColorScheme cs) {
    return TacticalSurface(
      style: TacticalSurfaceStyle.raised,
      padding: const EdgeInsets.all(NeptunSpacing.xl),
      child: Row(
        children: [
          Container(
            width: 56,
            height: 56,
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: [
                  cs.primary,
                  cs.primary.withValues(alpha: 0.85),
                ],
              ),
              borderRadius: BorderRadius.circular(18),
              boxShadow: [
                BoxShadow(
                  color: cs.primary.withValues(alpha: 0.25),
                  blurRadius: 12,
                  offset: const Offset(0, 4),
                ),
              ],
            ),
            child: Center(
              child: Text(
                _nickname.isNotEmpty ? _nickname[0].toUpperCase() : '?',
                style: GoogleFonts.plusJakartaSans(
                  fontSize: 24,
                  fontWeight: FontWeight.w700,
                  color: cs.onPrimary,
                ),
              ),
            ),
          ),
          const SizedBox(width: NeptunSpacing.lg),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  _nickname.isNotEmpty ? _nickname : 'Гість',
                  style: GoogleFonts.plusJakartaSans(
                    fontSize: 16,
                    fontWeight: FontWeight.w600,
                    color: cs.onSurface,
                  ),
                ),
                const SizedBox(height: 4),
                if (_isPremium)
                  StatusPill(
                    label: 'PRO',
                    variant: StatusPillVariant.warning,
                    icon: Icons.workspace_premium_rounded,
                  )
                else
                  Text(
                    'Безкоштовний план',
                    style: GoogleFonts.plusJakartaSans(
                      fontSize: 13,
                      color: cs.onSurface.withValues(alpha: 0.5),
                    ),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPremiumBanner(ColorScheme cs) {
    final gold = cs.tertiary;
    return TacticalSurface(
      style: TacticalSurfaceStyle.glow,
      accentGlow: gold,
      padding: const EdgeInsets.all(NeptunSpacing.xl),
      onTap: () {
        HapticFeedback.selectionClick();
        _push('/premium');
      },
      child: Row(
        children: [
          Container(
            width: 48,
            height: 48,
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: [gold, gold.withValues(alpha: 0.8)],
              ),
              borderRadius: BorderRadius.circular(14),
            ),
            child: Icon(
              Icons.workspace_premium_rounded,
              color: cs.onTertiary,
              size: 26,
            ),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Neptun PRO',
                  style: GoogleFonts.plusJakartaSans(
                    fontSize: 16,
                    fontWeight: FontWeight.w700,
                    color: cs.onSurface,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  'Без реклами • Аналітика • Історія',
                  style: GoogleFonts.plusJakartaSans(
                    fontSize: 13,
                    color: cs.onSurface.withValues(alpha: 0.55),
                  ),
                ),
              ],
            ),
          ),
          Icon(
            Icons.arrow_forward_ios_rounded,
            size: 16,
            color: cs.primary,
          ),
        ],
      ),
    );
  }
}
