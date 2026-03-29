import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../services/chat_service.dart';
import '../../models/chat_message.dart';
import '../di/service_locator.dart';

final chatServiceProvider = Provider<ChatService>((ref) => sl<ChatService>());

final chatMessagesProvider =
    StreamProvider<List<ChatMessage>>((ref) {
  final chat = ref.watch(chatServiceProvider);
  return chat.messagesStream.map((list) => list);
});

final chatOnlineCountProvider = StreamProvider<int>((ref) {
  final chat = ref.watch(chatServiceProvider);
  return chat.onlineStream;
});
