import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'chat_provider.dart';

final nicknameProvider = FutureProvider<String?>((ref) async {
  final chat = ref.watch(chatServiceProvider);
  await chat.init();
  return chat.nickname;
});

final deviceIdProvider = FutureProvider<String?>((ref) async {
  final chat = ref.watch(chatServiceProvider);
  await chat.init();
  return chat.deviceId;
});
