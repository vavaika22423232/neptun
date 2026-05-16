import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:neptun_alarm_app/models/chat_message.dart';
import 'package:neptun_alarm_app/services/chat_service.dart';

class ChatDialogHelpers {
  static void reportMessage(
    BuildContext context,
    ChatService chat,
    ChatMessage msg,
  ) {
    showDialog(
      context: context,
      builder: (ctx) {
        String? selectedReason;
        return StatefulBuilder(
          builder: (ctx, setDialogState) => AlertDialog(
            title: Text(
              'Поскаржитись',
              style: GoogleFonts.plusJakartaSans(
                fontSize: 16,
                fontWeight: FontWeight.w600,
              ),
            ),
            content: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  'Оберіть причину скарги:',
                  style: GoogleFonts.plusJakartaSans(fontSize: 14),
                ),
                const SizedBox(height: 12),
                RadioGroup<String>(
                  groupValue: selectedReason,
                  onChanged: (v) => setDialogState(() => selectedReason = v),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      for (final reason in [
                        'Спам',
                        'Образи або ненависть',
                        'Неправдива інформація',
                        'Загрози або насильство',
                        'Інше',
                      ])
                        RadioListTile<String>(
                          title: Text(
                            reason,
                            style: GoogleFonts.plusJakartaSans(fontSize: 14),
                          ),
                          value: reason,
                          dense: true,
                        ),
                    ],
                  ),
                ),
              ],
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(ctx),
                child: const Text('Скасувати'),
              ),
              FilledButton(
                onPressed: selectedReason == null
                    ? null
                    : () async {
                        Navigator.pop(ctx);
                        await chat.reportMessage(
                          msg.id,
                          selectedReason!,
                          reportedDeviceId: msg.deviceId,
                          reportedNickname: msg.userId,
                          originalText: msg.message,
                        );
                        if (context.mounted) {
                          ScaffoldMessenger.of(context).showSnackBar(
                            const SnackBar(
                              content: Text('Скаргу надіслано'),
                              backgroundColor: Colors.green,
                              behavior: SnackBarBehavior.floating,
                            ),
                          );
                        }
                      },
                child: const Text('Надіслати'),
              ),
            ],
          ),
        );
      },
    );
  }

  static Future<void> deleteAllMessagesFromUser(
    BuildContext context,
    ChatService chat,
    ChatMessage msg,
    VoidCallback onSuccess,
  ) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Видалити всі повідомлення'),
        content: Text(
          'Видалити всі повідомлення від ${msg.userId}? Цю дію не можна скасувати.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Скасувати'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            style: FilledButton.styleFrom(
              backgroundColor: Theme.of(ctx).colorScheme.error,
              foregroundColor: Theme.of(ctx).colorScheme.onError,
            ),
            child: const Text('Видалити всі'),
          ),
        ],
      ),
    );
    if (confirmed != true) return;
    final deleted = await chat.deleteAllUserMessages(
      nickname: msg.userId,
      deviceId: msg.deviceId,
    );
    if (context.mounted) {
      if (deleted != null && deleted > 0) {
        onSuccess();
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Видалено повідомлень: $deleted'),
            behavior: SnackBarBehavior.floating,
          ),
        );
      }
    }
  }

  static void blockUser(
    BuildContext context,
    ChatService chat,
    ChatMessage msg,
    VoidCallback onSuccess,
  ) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: Text(
          'Сховати користувача?',
          style: GoogleFonts.plusJakartaSans(
            fontSize: 16,
            fontWeight: FontWeight.w600,
          ),
        ),
        content: Text(
          'Повідомлення від ${msg.userId} більше не відображатимуться. Цю дію можна скасувати в налаштуваннях.',
          style: GoogleFonts.plusJakartaSans(fontSize: 14),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Скасувати'),
          ),
          FilledButton(
            onPressed: () {
              Navigator.pop(ctx);
              chat.blockUser(msg.userId);
              onSuccess();
              ScaffoldMessenger.of(context).showSnackBar(
                SnackBar(
                  content: Text('${msg.userId} приховано'),
                  behavior: SnackBarBehavior.floating,
                ),
              );
            },
            child: const Text('Сховати'),
          ),
        ],
      ),
    );
  }
}
