import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../core/widgets/neptun_card.dart';
import '../services/window_manager.dart';

class MenuPanel extends ConsumerStatefulWidget {
  const MenuPanel({super.key});

  @override
  ConsumerState<MenuPanel> createState() => _MenuPanelState();
}

class _MenuPanelState extends ConsumerState<MenuPanel> {
  bool _isLoading = true;
  String _userName = 'Користувач';
  bool _isPremium = false;

  @override
  void initState() {
    super.initState();
    _loadSettings();
  }

  Future<void> _loadSettings() async {
    final prefs = await SharedPreferences.getInstance();
    final userName = prefs.getString('anonymous_user_id') ?? 'Користувач';
    final isPremium = prefs.getBool('is_premium') ?? false;

    if (mounted) {
      setState(() {
        _userName = userName;
        _isPremium = isPremium;
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return NeptunCard(
      variant: NeptunCardVariant.elevated,
      padding: EdgeInsets.zero,
      child: Column(
        children: [
          // Header
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 16, 16, 12),
            child: Row(
              children: [
                Icon(
                  Icons.grid_view_rounded,
                  color: Theme.of(context).colorScheme.primary,
                  size: 20,
                ),
                const SizedBox(width: 8),
                Text(
                  'Меню',
                  style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    color: Theme.of(context).colorScheme.onSurface,
                  ),
                ),
              ],
            ),
          ),

          Divider(
            height: 1,
            color: Theme.of(
              context,
            ).colorScheme.outlineVariant.withValues(alpha: 0.3),
          ),

          // Content
          Expanded(
            child: _isLoading
                ? const Center(child: CircularProgressIndicator())
                : ListView(
                    padding: const EdgeInsets.fromLTRB(16, 12, 16, 32),
                    children: [
                      // 1. Profile Card (Top Row)
                      _buildProfileCard(),

                      const SizedBox(height: 12),

                      // 2. Premium Banner (Gold/Gradient)
                      _buildPremiumCard(),

                      const SizedBox(height: 12),

                      // 3. Full settings link (replaces duplicate toggles/cards)
                      _buildActionCard(
                        icon: Icons.settings_rounded,
                        title: 'Повні налаштування',
                        subtitle: 'Сповіщення, регіони, тема, звук',
                        onTap: () {
                          HapticFeedback.lightImpact();
                          WindowManager().closePanel();
                          context.go('/profile');
                        },
                      ),

                      const SizedBox(height: 24),

                      // Version
                      Center(
                        child: Text(
                          'NEPTUN SYSTEM v2.0',
                          style: TextStyle(
                            color: Theme.of(
                              context,
                            ).colorScheme.onSurface.withValues(alpha: 0.2),
                            fontSize: 10,
                            letterSpacing: 1.5,
                          ),
                        ),
                      ),
                    ],
                  ),
          ),
        ],
      ),
    );
  }

  Widget _buildProfileCard() {
    final colorScheme = Theme.of(context).colorScheme;
    return GestureDetector(
      onTap: () {
        context.push('/profile-page');
      },
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: colorScheme.surfaceContainer,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: colorScheme.outlineVariant),
        ),
        child: Row(
          children: [
            Container(
              width: 50,
              height: 50,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: colorScheme.primary,
              ),
              child: const Icon(Icons.person, color: Colors.white, size: 24),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    _userName,
                    style: TextStyle(
                      color: colorScheme.onSurface,
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Row(
                    children: [
                      Icon(
                        Icons.medical_information,
                        size: 12,
                        color: colorScheme.onSurfaceVariant,
                      ),
                      const SizedBox(width: 4),
                      Text(
                        'Мед. картка',
                        style: TextStyle(
                          color: colorScheme.onSurfaceVariant,
                          fontSize: 12,
                        ),
                      ),
                      const SizedBox(width: 8),
                      Container(
                        width: 1,
                        height: 10,
                        color: colorScheme.outlineVariant,
                      ),
                      const SizedBox(width: 8),
                      Icon(
                        Icons.backpack,
                        size: 12,
                        color: colorScheme.onSurfaceVariant,
                      ),
                      const SizedBox(width: 4),
                      Text(
                        'Валіза',
                        style: TextStyle(
                          color: colorScheme.onSurfaceVariant,
                          fontSize: 12,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            Icon(
              Icons.chevron_right,
              color: colorScheme.onSurface.withValues(alpha: 0.3),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildPremiumCard() {
    return GestureDetector(
      onTap: () {
        context.push('/premium');
      },
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: _isPremium
              ? Theme.of(context).colorScheme.surfaceContainerHighest
              : Color(0xFFFFD700).withValues(alpha: 0.12),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: _isPremium
                ? Theme.of(context).colorScheme.outline.withValues(alpha: 0.2)
                : Color(0xFFFFD700).withValues(alpha: 0.35),
          ),
        ),
        child: Row(
          children: [
            Icon(
              _isPremium ? Icons.verified : Icons.workspace_premium,
              color: _isPremium
                  ? Theme.of(context).colorScheme.primary
                  : Colors.amber,
              size: 28,
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    _isPremium ? 'PREMIUM АКТИВОВАНО' : 'ОТРИМАТИ PREMIUM',
                    style: TextStyle(
                      color: _isPremium ? Colors.white : Colors.amber,
                      fontSize: 14,
                      fontWeight: FontWeight.bold,
                      letterSpacing: 0.5,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    _isPremium
                        ? 'Дякуємо за підтримку'
                        : 'Без реклами та обмежень',
                    style: TextStyle(color: Colors.white70, fontSize: 12),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildActionCard({
    required IconData icon,
    required String title,
    required String subtitle,
    required VoidCallback onTap,
    Color? color,
  }) {
    final colorScheme = Theme.of(context).colorScheme;
    final iconColor = color ?? colorScheme.primary;
    return GestureDetector(
      onTap: () {
        HapticFeedback.lightImpact();
        onTap();
      },
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: colorScheme.surfaceContainer,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: colorScheme.outlineVariant),
        ),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: iconColor.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Icon(icon, color: iconColor, size: 20),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: TextStyle(
                      color: colorScheme.onSurface,
                      fontSize: 14,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  Text(
                    subtitle,
                    style: TextStyle(
                      color: colorScheme.onSurfaceVariant,
                      fontSize: 12,
                    ),
                  ),
                ],
              ),
            ),
            Icon(
              Icons.arrow_forward_ios_rounded,
              color: colorScheme.onSurface.withValues(alpha: 0.3),
              size: 14,
            ),
          ],
        ),
      ),
    );
  }
}
