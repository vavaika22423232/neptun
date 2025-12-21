import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'dart:math';
import 'dart:async';

class ChatPage extends StatefulWidget {
  const ChatPage({super.key});

  @override
  State<ChatPage> createState() => _ChatPageState();
}

class _ChatPageState extends State<ChatPage> {
  final TextEditingController _messageController = TextEditingController();
  final ScrollController _scrollController = ScrollController();
  List<ChatMessage> _messages = [];
  bool _isLoading = true;
  String? _myUserId;
  Timer? _refreshTimer;

  @override
  void initState() {
    super.initState();
    _initUserId();
    _loadMessages();
    // Auto-refresh every 5 seconds
    _refreshTimer = Timer.periodic(const Duration(seconds: 5), (_) {
      _loadMessages(showLoading: false);
    });
  }

  @override
  void dispose() {
    _messageController.dispose();
    _scrollController.dispose();
    _refreshTimer?.cancel();
    super.dispose();
  }

  Future<void> _initUserId() async {
    final prefs = await SharedPreferences.getInstance();
    String? savedId = prefs.getString('anonymous_user_id');
    
    if (savedId == null) {
      // Generate random anonymous ID
      savedId = _generateAnonymousId();
      await prefs.setString('anonymous_user_id', savedId);
    }
    
    setState(() {
      _myUserId = savedId;
    });
  }

  String _generateAnonymousId() {
    final random = Random();
    final adjectives = [
      'Синій', 'Зелений', 'Червоний', 'Жовтий', 'Білий', 
      'Чорний', 'Сірий', 'Помаранчевий', 'Фіолетовий', 'Рожевий',
      'Швидкий', 'Сміливий', 'Тихий', 'Мудрий', 'Веселий',
      'Хоробрий', 'Спокійний', 'Сильний', 'Вільний', 'Добрий'
    ];
    final animals = [
      'Лев', 'Орел', 'Вовк', 'Ведмідь', 'Сокіл',
      'Тигр', 'Пантера', 'Яструб', 'Дельфін', 'Лис',
      'Олень', 'Барсук', 'Рись', 'Бізон', 'Кіт',
      'Пес', 'Їжак', 'Заєць', 'Бобер', 'Козак'
    ];
    
    final adjective = adjectives[random.nextInt(adjectives.length)];
    final animal = animals[random.nextInt(animals.length)];
    final number = random.nextInt(999) + 1;
    
    return '$adjective$animal$number';
  }

  Future<void> _loadMessages({bool showLoading = true}) async {
    if (showLoading) {
      setState(() => _isLoading = true);
    }

    try {
      final response = await http.get(
        Uri.parse('https://neptun.in.ua/api/chat/messages'),
      );

      if (response.statusCode == 200) {
        final data = json.decode(utf8.decode(response.bodyBytes));
        setState(() {
          _messages = (data['messages'] as List)
              .map((m) => ChatMessage.fromJson(m))
              .toList();
          _isLoading = false;
        });
      }
    } catch (e) {
      debugPrint('Error loading chat messages: $e');
      setState(() => _isLoading = false);
    }
  }

  Future<void> _sendMessage() async {
    final text = _messageController.text.trim();
    if (text.isEmpty || _myUserId == null) return;

    _messageController.clear();

    try {
      final response = await http.post(
        Uri.parse('https://neptun.in.ua/api/chat/send'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'user_id': _myUserId,
          'message': text,
        }),
      );

      if (response.statusCode == 200) {
        await _loadMessages(showLoading: false);
        // Scroll to bottom
        WidgetsBinding.instance.addPostFrameCallback((_) {
          if (_scrollController.hasClients) {
            _scrollController.animateTo(
              _scrollController.position.maxScrollExtent,
              duration: const Duration(milliseconds: 300),
              curve: Curves.easeOut,
            );
          }
        });
      }
    } catch (e) {
      debugPrint('Error sending message: $e');
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Помилка надсилання повідомлення')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    
    return Scaffold(
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('💬 Чат'),
            if (_myUserId != null)
              Text(
                'Ви: $_myUserId',
                style: TextStyle(
                  fontSize: 12,
                  color: isDark ? Colors.grey[400] : Colors.grey[600],
                ),
              ),
          ],
        ),
        backgroundColor: isDark ? const Color(0xFF1E1E1E) : Theme.of(context).colorScheme.inversePrimary,
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: () => _loadMessages(),
          ),
        ],
      ),
      body: Column(
        children: [
          // Chat rules banner
          Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            color: isDark ? Colors.orange.shade900.withOpacity(0.3) : Colors.orange.shade50,
            child: Row(
              children: [
                Icon(Icons.info_outline, size: 16, color: Colors.orange.shade700),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    'Будьте ввічливі. Не поширюйте фейки та паніку.',
                    style: TextStyle(
                      fontSize: 12,
                      color: Colors.orange.shade700,
                    ),
                  ),
                ),
              ],
            ),
          ),
          
          // Messages list
          Expanded(
            child: _isLoading
                ? const Center(child: CircularProgressIndicator())
                : _messages.isEmpty
                    ? Center(
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(
                              Icons.chat_bubble_outline,
                              size: 64,
                              color: isDark ? Colors.grey[600] : Colors.grey[400],
                            ),
                            const SizedBox(height: 16),
                            Text(
                              'Поки що немає повідомлень',
                              style: TextStyle(
                                color: isDark ? Colors.grey[400] : Colors.grey[600],
                              ),
                            ),
                            const SizedBox(height: 8),
                            Text(
                              'Будьте першим!',
                              style: TextStyle(
                                color: isDark ? Colors.grey[500] : Colors.grey[500],
                                fontSize: 12,
                              ),
                            ),
                          ],
                        ),
                      )
                    : ListView.builder(
                        controller: _scrollController,
                        padding: const EdgeInsets.all(8),
                        itemCount: _messages.length,
                        itemBuilder: (context, index) {
                          final message = _messages[index];
                          final isMe = message.userId == _myUserId;
                          
                          return _buildMessageBubble(message, isMe, isDark);
                        },
                      ),
          ),
          
          // Input field
          Container(
            padding: EdgeInsets.only(
              left: 16,
              right: 8,
              top: 8,
              bottom: MediaQuery.of(context).padding.bottom + 8,
            ),
            decoration: BoxDecoration(
              color: isDark ? const Color(0xFF2D2D2D) : Colors.white,
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withOpacity(0.1),
                  blurRadius: 4,
                  offset: const Offset(0, -2),
                ),
              ],
            ),
            child: Row(
              children: [
                Expanded(
                  child: TextField(
                    controller: _messageController,
                    decoration: InputDecoration(
                      hintText: 'Написати повідомлення...',
                      hintStyle: TextStyle(
                        color: isDark ? Colors.grey[500] : Colors.grey[400],
                      ),
                      border: OutlineInputBorder(
                        borderRadius: BorderRadius.circular(24),
                        borderSide: BorderSide.none,
                      ),
                      filled: true,
                      fillColor: isDark ? const Color(0xFF3D3D3D) : Colors.grey[100],
                      contentPadding: const EdgeInsets.symmetric(
                        horizontal: 16,
                        vertical: 10,
                      ),
                    ),
                    style: TextStyle(
                      color: isDark ? Colors.white : Colors.black,
                    ),
                    maxLines: 3,
                    minLines: 1,
                    textCapitalization: TextCapitalization.sentences,
                    onSubmitted: (_) => _sendMessage(),
                  ),
                ),
                const SizedBox(width: 8),
                Container(
                  decoration: BoxDecoration(
                    color: Theme.of(context).primaryColor,
                    shape: BoxShape.circle,
                  ),
                  child: IconButton(
                    icon: const Icon(Icons.send, color: Colors.white),
                    onPressed: _sendMessage,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildMessageBubble(ChatMessage message, bool isMe, bool isDark) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: isMe ? MainAxisAlignment.end : MainAxisAlignment.start,
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          if (!isMe) ...[
            CircleAvatar(
              radius: 16,
              backgroundColor: _getColorForUserId(message.userId),
              child: Text(
                message.userId.isNotEmpty ? message.userId[0].toUpperCase() : '?',
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 14,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
            const SizedBox(width: 8),
          ],
          Flexible(
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
              decoration: BoxDecoration(
                color: isMe
                    ? Theme.of(context).primaryColor
                    : (isDark ? const Color(0xFF3D3D3D) : Colors.grey[200]),
                borderRadius: BorderRadius.only(
                  topLeft: const Radius.circular(18),
                  topRight: const Radius.circular(18),
                  bottomLeft: Radius.circular(isMe ? 18 : 4),
                  bottomRight: Radius.circular(isMe ? 4 : 18),
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  if (!isMe)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 4),
                      child: Text(
                        message.userId,
                        style: TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.bold,
                          color: _getColorForUserId(message.userId),
                        ),
                      ),
                    ),
                  Text(
                    message.text,
                    style: TextStyle(
                      color: isMe ? Colors.white : (isDark ? Colors.white : Colors.black87),
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    message.formattedTime,
                    style: TextStyle(
                      fontSize: 10,
                      color: isMe
                          ? Colors.white.withOpacity(0.7)
                          : (isDark ? Colors.grey[500] : Colors.grey[600]),
                    ),
                  ),
                ],
              ),
            ),
          ),
          if (isMe) const SizedBox(width: 8),
        ],
      ),
    );
  }

  Color _getColorForUserId(String id) {
    final colors = [
      Colors.blue,
      Colors.green,
      Colors.orange,
      Colors.purple,
      Colors.teal,
      Colors.pink,
      Colors.indigo,
      Colors.cyan,
      Colors.amber.shade700,
      Colors.red.shade400,
    ];
    
    final hash = id.hashCode.abs();
    return colors[hash % colors.length];
  }
}

class ChatMessage {
  final String id;
  final String userId;
  final String text;
  final DateTime timestamp;

  ChatMessage({
    required this.id,
    required this.userId,
    required this.text,
    required this.timestamp,
  });

  factory ChatMessage.fromJson(Map<String, dynamic> json) {
    return ChatMessage(
      id: json['id'] ?? '',
      userId: json['user_id'] ?? 'Анонім',
      text: json['message'] ?? '',
      timestamp: DateTime.tryParse(json['timestamp'] ?? '') ?? DateTime.now(),
    );
  }

  String get formattedTime {
    final now = DateTime.now();
    final diff = now.difference(timestamp);
    
    if (diff.inMinutes < 1) {
      return 'Щойно';
    } else if (diff.inMinutes < 60) {
      return '${diff.inMinutes} хв тому';
    } else if (diff.inHours < 24) {
      return '${diff.inHours} год тому';
    } else {
      return '${timestamp.day}.${timestamp.month.toString().padLeft(2, '0')} ${timestamp.hour}:${timestamp.minute.toString().padLeft(2, '0')}';
    }
  }
}
