import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';

class HomeFeedPage extends StatefulWidget {
  const HomeFeedPage({super.key});

  @override
  State<HomeFeedPage> createState() => _HomeFeedPageState();
}

class _HomeFeedPageState extends State<HomeFeedPage> {
  String _userName = 'Користувач';

  @override
  void initState() {
    super.initState();
    _loadUserName();
  }

  Future<void> _loadUserName() async {
    final prefs = await SharedPreferences.getInstance();
    final name = prefs.getString('anonymous_user_id');
    if (name != null && name.isNotEmpty) {
      if (mounted) setState(() => _userName = name);
    }
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;

    return SafeArea(
      child: ListView(
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Доброго ранку,',
                    style: TextStyle(
                      fontSize: 16,
                      color: cs.onSurface.withValues(alpha: 0.6),
                    ),
                  ),
                  Text(
                    _userName,
                    style: TextStyle(
                      fontSize: 24,
                      fontWeight: FontWeight.bold,
                      color: cs.onSurface,
                    ),
                  ),
                ],
              ),
              Container(
                width: 50,
                height: 50,
                decoration: BoxDecoration(
                  color: cs.surfaceContainer,
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: cs.outline),
                ),
                child: Icon(
                  Icons.notifications_outlined,
                  color: cs.primary,
                ),
              ),
            ],
          ),

          const SizedBox(height: 24),

          SizedBox(
            height: 100,
            child: ListView(
              scrollDirection: Axis.horizontal,
              clipBehavior: Clip.none,
              children: [
                _buildStatusItem(context, 'Мій статус', Icons.add, isMe: true),
                const SizedBox(width: 12),
                _buildStatusItem(context, 'Дружина', Icons.face_3),
                const SizedBox(width: 12),
                _buildStatusItem(context, 'Син', Icons.face_6),
                const SizedBox(width: 12),
                _buildStatusItem(context, 'Офіс', Icons.apartment),
              ],
            ),
          ),

          const SizedBox(height: 30),

          Container(
            decoration: BoxDecoration(
              color: cs.surfaceContainer,
              borderRadius: BorderRadius.circular(24),
              border: Border.all(color: cs.outline),
            ),
            child: Column(
              children: [
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(10),
                      decoration: BoxDecoration(
                        color: cs.secondary,
                        shape: BoxShape.circle,
                      ),
                      child: const Icon(
                        Icons.check,
                        color: Colors.white,
                        size: 20,
                      ),
                    ),
                    const SizedBox(width: 12),
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Все спокійно',
                          style: TextStyle(
                            fontSize: 18,
                            fontWeight: FontWeight.bold,
                            color: cs.onSurface,
                          ),
                        ),
                        Text(
                          'Київська область',
                          style: TextStyle(
                            fontSize: 14,
                            color: cs.onSurface.withValues(alpha: 0.6),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
                const SizedBox(height: 20),
                Container(
                  height: 150,
                  width: double.infinity,
                  decoration: BoxDecoration(
                    color: cs.error.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(16),
                  ),
                  child: Center(
                    child: Icon(
                      Icons.map_rounded,
                      size: 64,
                      color: cs.error,
                    ),
                  ),
                ),
              ],
            ),
          ),

          const SizedBox(height: 30),

          Row(
            children: [
              Expanded(
                child: Container(
                  height: 180,
                  decoration: BoxDecoration(
                    color: cs.tertiary.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(24),
                    border: Border.all(color: cs.outline),
                  ),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Icon(Icons.bolt, size: 40, color: cs.tertiary),
                      const SizedBox(height: 8),
                      Text(
                        "Світло: Є",
                        style: TextStyle(
                          fontWeight: FontWeight.bold,
                          color: cs.onSurface,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  children: [
                    Container(
                      height: 82,
                      width: double.infinity,
                      decoration: BoxDecoration(
                        color: cs.surfaceContainer,
                        borderRadius: BorderRadius.circular(24),
                        border: Border.all(color: cs.outline),
                      ),
                      child: Center(
                        child: Icon(
                          Icons.water_drop,
                          color: cs.error,
                        ),
                      ),
                    ),
                    const SizedBox(height: 16),
                    Container(
                      height: 82,
                      width: double.infinity,
                      decoration: BoxDecoration(
                        color: cs.surfaceContainer,
                        borderRadius: BorderRadius.circular(24),
                        border: Border.all(color: cs.outline),
                      ),
                      child: Center(
                        child: Icon(Icons.wifi, color: cs.inversePrimary),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),

          const SizedBox(height: 100),
        ],
      ),
    );
  }

  Widget _buildStatusItem(
    BuildContext context,
    String label,
    IconData icon, {
    bool isMe = false,
  }) {
    final cs = Theme.of(context).colorScheme;
    return Column(
      children: [
        Container(
          width: 64,
          height: 64,
          decoration: BoxDecoration(
            color: isMe
                ? cs.error
                : cs.onSurface.withValues(alpha: 0.08),
            shape: BoxShape.circle,
            border: Border.all(
              color: isMe
                  ? Colors.transparent
                  : cs.error.withValues(alpha: 0.5),
              width: 2,
            ),
            boxShadow: [
              if (isMe)
                BoxShadow(
                  color: cs.error.withValues(alpha: 0.4),
                  blurRadius: 10,
                  offset: const Offset(0, 4),
                ),
            ],
          ),
          child: Icon(
            icon,
            color: isMe ? Colors.white : cs.onSurface,
            size: 28,
          ),
        ),
        const SizedBox(height: 8),
        Text(
          label,
          style: TextStyle(
            fontSize: 12,
            fontWeight: FontWeight.w500,
            color: cs.onSurface,
          ),
        ),
      ],
    );
  }
}
