import 'package:flutter/material.dart';

class MenuPage extends StatelessWidget {
  const MenuPage({super.key});

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Scaffold(
      backgroundColor: cs.surface,
      appBar: AppBar(
        backgroundColor: cs.surfaceContainer,
        title: Text(
          'Меню',
          style: TextStyle(
            color: cs.onSurface,
            fontWeight: FontWeight.bold,
          ),
        ),
        elevation: 0,
        centerTitle: true,
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          _buildMenuItem(context, Icons.person, 'Профіль', 'Налаштування акаунту'),
          const SizedBox(height: 12),
          _buildMenuItem(
            context,
            Icons.star,
            'Premium',
            'Управління підпискою',
            isPremium: true,
          ),
          const SizedBox(height: 12),
          _buildMenuItem(context, Icons.settings, 'Загальні', 'Мова, тема, сповіщення'),
          const SizedBox(height: 24),
          Center(
            child: Text(
              'Версія 1.0.0',
              style: TextStyle(color: cs.onSurface.withValues(alpha: 0.5), fontSize: 12),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildMenuItem(
    BuildContext context,
    IconData icon,
    String title,
    String subtitle, {
    bool isPremium = false,
  }) {
    final cs = Theme.of(context).colorScheme;
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: cs.surfaceContainer,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: cs.outline),
      ),
      child: Row(
        children: [
          Icon(icon, color: isPremium ? Colors.amber : cs.onSurface),
          const SizedBox(width: 16),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: TextStyle(
                  color: cs.onSurface,
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                ),
              ),
              Text(
                subtitle,
                style: TextStyle(color: cs.onSurface.withValues(alpha: 0.5), fontSize: 12),
              ),
            ],
          ),
          const Spacer(),
          Icon(Icons.chevron_right, color: cs.onSurface.withValues(alpha: 0.5)),
        ],
      ),
    );
  }
}
