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
import '../app_shell.dart';

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
    final topInset =
        MediaQuery.of(context).padding.top +
        AppShellState.chromeHeight +
        AppShellState.contentTopGap;

    return ListView(
      padding: EdgeInsets.fromLTRB(
        NeptunSpacing.lg,
        topInset,
        NeptunSpacing.lg,
        NeptunSpacing.xxxl,
      ),
      children: [
        Text(
          'Профіль',
          style: GoogleFonts.plusJakartaSans(
            fontSize: 29,
            fontWeight: FontWeight.w900,
            color: cs.onSurface,
            height: 1.05,
          ),
        ),
        const SizedBox(height: 12),
        Text(
          'Налаштування застосунку та сповіщень',
          style: GoogleFonts.plusJakartaSans(
            fontSize: 15,
            fontWeight: FontWeight.w800,
            color: cs.onSurface.withValues(alpha: 0.62),
          ),
        ),
        const SizedBox(height: 18),
        Text(
          '${_nickname.isNotEmpty ? _nickname : 'Гість'} · ${_isPremium ? 'PREMIUM' : 'FREE'}',
          style: GoogleFonts.plusJakartaSans(
            fontSize: 14,
            fontWeight: FontWeight.w700,
            color: cs.onSurface.withValues(alpha: 0.82),
          ),
        ),
        const SizedBox(height: 18),

        _buildPremiumBanner(cs),
        const SizedBox(height: NeptunSpacing.xl),

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
                SectionHeader(
                  title: 'Модерація',
                  icon: Icons.admin_panel_settings_rounded,
                ),
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

  Widget _buildPremiumBanner(ColorScheme cs) {
    const gold = Color(0xFFDDBB5B);
    return TacticalSurface(
      style: TacticalSurfaceStyle.glow,
      accentGlow: gold,
      padding: const EdgeInsets.all(18),
      onTap: () {
        HapticFeedback.selectionClick();
        _push('/premium');
      },
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 50,
            height: 50,
            decoration: BoxDecoration(
              color: gold.withValues(alpha: 0.16),
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: gold.withValues(alpha: 0.35), width: 1),
            ),
            child: Icon(Icons.workspace_premium_rounded, color: gold, size: 27),
          ),
          const SizedBox(width: 14),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'NEPTUN Premium ✦',
                  style: GoogleFonts.plusJakartaSans(
                    fontSize: 19,
                    fontWeight: FontWeight.w900,
                    color: cs.onSurface,
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  'Розширені можливості',
                  style: GoogleFonts.plusJakartaSans(
                    fontSize: 13,
                    fontWeight: FontWeight.w800,
                    color: cs.onSurface.withValues(alpha: 0.58),
                  ),
                ),
                const SizedBox(height: 16),
                _premiumBullet('Детальні карти загроз', gold, cs),
                const SizedBox(height: 12),
                _premiumBullet('Пріоритетні сповіщення', gold, cs),
                const SizedBox(height: 12),
                _premiumBullet('Статистика та аналітика', gold, cs),
              ],
            ),
          ),
          Icon(Icons.arrow_forward_ios_rounded, size: 20, color: gold),
        ],
      ),
    );
  }

  Widget _premiumBullet(String text, Color gold, ColorScheme cs) {
    return Row(
      children: [
        Container(
          width: 7,
          height: 7,
          decoration: BoxDecoration(color: gold, shape: BoxShape.circle),
        ),
        const SizedBox(width: 16),
        Expanded(
          child: Text(
            text,
            style: GoogleFonts.plusJakartaSans(
              fontSize: 14,
              fontWeight: FontWeight.w800,
              color: cs.onSurface.withValues(alpha: 0.78),
            ),
          ),
        ),
      ],
    );
  }
}
