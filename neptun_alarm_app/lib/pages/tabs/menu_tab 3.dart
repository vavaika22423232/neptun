import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:url_launcher/url_launcher.dart';
import '../../core/utils/open_neptun_telegram.dart';
import '../../core/widgets/neptun_overlay_insets.dart';
import '../../services/purchase_service.dart';
import '../../services/tts_service.dart';
import '../../services/moderator_service.dart';

/// Menu tab — profile, premium, toggles, links
class MenuTab extends StatefulWidget {
  const MenuTab({super.key});

  @override
  State<MenuTab> createState() => _MenuTabState();
}

class _MenuTabState extends State<MenuTab> with AutomaticKeepAliveClientMixin {
  @override
  bool get wantKeepAlive => true;

  String _nickname = '';
  bool _isPremium = false;
  bool _ttsEnabled = false;

  @override
  void initState() {
    super.initState();
    _loadSettings();
  }

  Future<void> _loadSettings() async {
    final prefs = await SharedPreferences.getInstance();
    final premium = PurchaseService().isPremium;
    final tts = TtsService().isEnabled;
    if (mounted) {
      setState(() {
        _nickname = prefs.getString('chat_nickname') ?? '';
        _isPremium = premium;
        _ttsEnabled = tts;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    super.build(context);
    final cs = Theme.of(context).colorScheme;
    final tt = Theme.of(context).textTheme;

    final topInset = neptunContentTopPadding(context) + 16;
    final bottomInset = neptunContentBottomPadding(context);

    return ListView(
      padding: EdgeInsets.fromLTRB(16, topInset, 16, bottomInset),
      children: [
        // ─── Header ───
        Padding(
          padding: const EdgeInsets.only(bottom: 20),
          child: Text('Меню', style: tt.headlineMedium),
        ),

        // ─── Profile Card ───
        _buildProfileCard(cs, tt),
        const SizedBox(height: 20),

        // ─── Premium Banner ───
        if (!_isPremium) ...[
          _buildPremiumBanner(cs, tt),
          const SizedBox(height: 20),
        ],

        // ─── Settings Section ───
        _sectionLabel('НАЛАШТУВАННЯ', cs, tt),
        const SizedBox(height: 8),
        _buildSettingsTile(
          icon: Icons.record_voice_over_rounded,
          label: 'Голосові сповіщення',
          cs: cs,
          tt: tt,
          trailing: Switch.adaptive(
            value: _ttsEnabled,
            activeTrackColor: cs.primary,
            onChanged: (v) async {
              await TtsService().setEnabled(v);
              setState(() => _ttsEnabled = v);
            },
          ),
        ),
        const SizedBox(height: 20),

        // ─── Links Section ───
        _sectionLabel('ПОСИЛАННЯ', cs, tt),
        const SizedBox(height: 8),
        _buildSettingsTile(
          icon: Icons.telegram,
          label: 'Telegram — швидші алерти',
          cs: cs,
          tt: tt,
          onTap: () => openNeptunTelegramChannel('menu'),
        ),
        _buildSettingsTile(
          icon: Icons.language_rounded,
          label: 'Вебсайт neptun.in.ua',
          cs: cs,
          tt: tt,
          onTap: () => launchUrl(
            Uri.parse('https://neptun.in.ua'),
            mode: LaunchMode.externalApplication,
          ),
        ),
        _buildSettingsTile(
          icon: Icons.feedback_rounded,
          label: 'Зворотній зв\'язок',
          cs: cs,
          tt: tt,
          onTap: () => context.push('/feedback'),
        ),
        // Moderator feedback moderation link
        StreamBuilder<bool>(
          stream: ModeratorService.instance.stream,
          initialData: ModeratorService.instance.isModerator,
          builder: (context, snap) {
            if (snap.data != true) return const SizedBox.shrink();
            return _buildSettingsTile(
              icon: Icons.admin_panel_settings_rounded,
              label: 'Модерація відгуків',
              cs: cs,
              tt: tt,
              onTap: () => context.push('/feedback-moderation'),
            );
          },
        ),
        const SizedBox(height: 24),

        // ─── Version ───
        Center(
          child: Text(
            'Neptun v1.7.0',
            style: tt.bodySmall?.copyWith(
              color: cs.onSurface.withValues(alpha: 0.25),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildProfileCard(ColorScheme cs, TextTheme tt) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: cs.surfaceContainer,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: cs.outline),
      ),
      child: Row(
        children: [
          // Avatar
          Container(
            width: 52,
            height: 52,
            decoration: BoxDecoration(
              color: cs.primary.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(16),
            ),
            child: Center(
              child: Text(
                _nickname.isNotEmpty ? _nickname[0].toUpperCase() : '?',
                style: tt.headlineSmall?.copyWith(
                  color: cs.primary,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  _nickname.isNotEmpty ? _nickname : 'Гість',
                  style: tt.titleMedium?.copyWith(fontWeight: FontWeight.w600),
                ),
                const SizedBox(height: 2),
                Row(
                  children: [
                    if (_isPremium)
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 8,
                          vertical: 2,
                        ),
                        decoration: BoxDecoration(
                          color: cs.tertiary.withValues(alpha: 0.15),
                          borderRadius: BorderRadius.circular(6),
                        ),
                        child: Text(
                          'PRO',
                          style: tt.labelSmall?.copyWith(
                            color: cs.tertiary,
                            fontWeight: FontWeight.w800,
                            fontSize: 10,
                          ),
                        ),
                      )
                    else
                      Text(
                        'Безкоштовний план',
                        style: tt.bodySmall?.copyWith(
                          color: cs.onSurface.withValues(alpha: 0.5),
                        ),
                      ),
                  ],
                ),
              ],
            ),
          ),
          Icon(
            Icons.chevron_right_rounded,
            color: cs.onSurface.withValues(alpha: 0.3),
          ),
        ],
      ),
    );
  }

  Widget _buildPremiumBanner(ColorScheme cs, TextTheme tt) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: () => context.push('/premium'),
        borderRadius: BorderRadius.circular(18),
        child: Container(
          padding: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: cs.surfaceContainerHighest.withValues(alpha: 0.85),
            borderRadius: BorderRadius.circular(18),
            border: Border.all(color: cs.outline.withValues(alpha: 0.15)),
          ),
          child: Row(
            children: [
              Container(
                width: 44,
                height: 44,
                decoration: BoxDecoration(
                  color: cs.tertiary.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Icon(
                  Icons.workspace_premium_rounded,
                  color: cs.tertiary,
                  size: 24,
                ),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Neptun PRO',
                      style: tt.titleSmall?.copyWith(
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(
                      'Без реклами • Більше функцій',
                      style: tt.bodySmall?.copyWith(
                        color: cs.onSurface.withValues(alpha: 0.5),
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
        ),
      ),
    );
  }

  Widget _sectionLabel(String text, ColorScheme cs, TextTheme tt) {
    return Padding(
      padding: const EdgeInsets.only(left: 4),
      child: Text(
        text,
        style: tt.labelSmall?.copyWith(
          letterSpacing: 1.2,
          color: cs.onSurface.withValues(alpha: 0.4),
        ),
      ),
    );
  }

  Widget _buildSettingsTile({
    required IconData icon,
    required String label,
    required ColorScheme cs,
    required TextTheme tt,
    VoidCallback? onTap,
    Widget? trailing,
  }) {
    return Material(
      color: Colors.transparent,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(14),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
          child: Row(
            children: [
              Icon(icon, size: 22, color: cs.primary),
              const SizedBox(width: 14),
              Expanded(
                child: Text(
                  label,
                  style: tt.bodyMedium?.copyWith(fontWeight: FontWeight.w500),
                ),
              ),
              if (trailing != null)
                trailing
              else if (onTap != null)
                Icon(
                  Icons.chevron_right_rounded,
                  size: 20,
                  color: cs.onSurface.withValues(alpha: 0.3),
                ),
            ],
          ),
        ),
      ),
    );
  }
}
