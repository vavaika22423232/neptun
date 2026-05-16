import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../config/app_constants.dart';

class ChangelogDialog {
  static const String _lastShownVersionKey = 'changelog_last_shown_version';
  static String get currentVersion => AppConstants.appVersion;

  /// Перевіряє чи потрібно показати changelog та показує його якщо потрібно
  static Future<void> showIfNeeded(BuildContext context) async {
    final prefs = await SharedPreferences.getInstance();
    final lastShownVersion = prefs.getString(_lastShownVersionKey);

    // Показуємо тільки якщо версія змінилась або ніколи не показували
    if (lastShownVersion != currentVersion) {
      if (context.mounted) {
        await _show(context);
        await prefs.setString(_lastShownVersionKey, currentVersion);
      }
    }
  }

  static Future<void> _show(BuildContext context) async {
    return showDialog(
      context: context,
      barrierDismissible: false,
      builder: (BuildContext context) {
        return Dialog(
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(24),
          ),
          backgroundColor: Colors.transparent,
          child: Container(
            constraints: const BoxConstraints(maxWidth: 400),
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: [
                  Color(0xFF1E3A8A), // Темно-синій
                  Color(0xFF3B82F6), // Яскраво-синій
                  Color(0xFF60A5FA), // Світло-синій
                ],
              ),
              borderRadius: BorderRadius.circular(24),
              boxShadow: [
                BoxShadow(
                  color: Colors.blue.withValues(alpha: 0.5),
                  blurRadius: 20,
                  spreadRadius: 5,
                  offset: const Offset(0, 10),
                ),
              ],
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                // Header
                Container(
                  padding: const EdgeInsets.fromLTRB(20, 20, 20, 16),
                  child: Column(
                    children: [
                      // Іконка оновлення
                      Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: Colors.white.withValues(alpha: 0.2),
                          shape: BoxShape.circle,
                        ),
                        child: const Icon(
                          Icons.auto_awesome,
                          size: 32,
                          color: Colors.white,
                        ),
                      ),
                      const SizedBox(height: 12),
                      const Text(
                        'Що нового?',
                        style: TextStyle(
                          fontSize: 22,
                          fontWeight: FontWeight.bold,
                          color: Colors.white,
                        ),
                      ),
                      const SizedBox(height: 6),
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 12,
                          vertical: 4,
                        ),
                        decoration: BoxDecoration(
                          color: Colors.white.withValues(alpha: 0.2),
                          borderRadius: BorderRadius.circular(16),
                        ),
                        child: Text(
                          'Версія $currentVersion',
                          style: const TextStyle(
                            fontSize: 12,
                            color: Colors.white,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),

                // Changelog items
                Container(
                  margin: const EdgeInsets.symmetric(horizontal: 12),
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(14),
                  ),
                  child: Column(
                    children: [
                      _buildChangeItem(
                        icon: Icons.cloud_off_rounded,
                        iconColor: const Color(0xFF10B981),
                        title: 'Офлайн-очередь повідомлень',
                        description: 'Повідомлення зберігаються при відсутності мережі та відправляються автоматично після відновлення',
                      ),
                      const SizedBox(height: 10),
                      _buildChangeItem(
                        icon: Icons.photo_camera_rounded,
                        iconColor: const Color(0xFF3B82F6),
                        title: 'Фото в чаті',
                        description: 'Відправка фото з галереї та камери. Підтримка HEIC з iPhone',
                      ),
                      const SizedBox(height: 10),
                      _buildChangeItem(
                        icon: Icons.dark_mode_rounded,
                        iconColor: const Color(0xFF6366F1),
                        title: 'Покращена темна тема чату',
                        description: 'Чужі повідомлення тепер добре видно на темному фоні',
                      ),
                    ],
                  ),
                ),

                // Footer з кнопкою
                Padding(
                  padding: const EdgeInsets.all(16),
                  child: SizedBox(
                    width: double.infinity,
                    child: ElevatedButton(
                      onPressed: () {
                        HapticFeedback.mediumImpact();
                        Navigator.of(context).pop();
                      },
                      style: ElevatedButton.styleFrom(
                        backgroundColor: Colors.white,
                        foregroundColor: const Color(0xFF1E3A8A),
                        padding: const EdgeInsets.symmetric(vertical: 12),
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(10),
                        ),
                        elevation: 0,
                      ),
                      child: const Text(
                        'Зрозуміло!',
                        style: TextStyle(
                          fontSize: 15,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  static Widget _buildChangeItem({
    required IconData icon,
    required Color iconColor,
    required String title,
    required String description,
  }) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Іконка
        Container(
          padding: const EdgeInsets.all(6),
          decoration: BoxDecoration(
            color: iconColor.withValues(alpha: 0.1),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Icon(
            icon,
            color: iconColor,
            size: 20,
          ),
        ),
        const SizedBox(width: 10),
        // Текст
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                title,
                style: const TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.bold,
                  color: Color(0xFF1F2937),
                ),
              ),
              const SizedBox(height: 2),
              Text(
                description,
                style: const TextStyle(
                  fontSize: 12,
                  color: Color(0xFF6B7280),
                  height: 1.3,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}
