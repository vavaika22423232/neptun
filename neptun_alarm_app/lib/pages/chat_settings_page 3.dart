import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/providers/chat_provider.dart';
import '../features/chat/presentation/widgets/chat_settings_sheet.dart';

/// Екран налаштувань чату. Відкривається з [AppShell] через
/// `Navigator.of(_, rootNavigator: true).push(MaterialPageRoute(...))`, щоб уникнути
/// конфлікту вкладеного навігатора shell з [GoRouter.push].
class ChatSettingsPage extends ConsumerWidget {
  const ChatSettingsPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return ChatSettingsSheet(
      chat: ref.read(chatServiceProvider),
      onNicknameChanged: () {},
    );
  }
}
