import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter/foundation.dart';
import 'package:webview_flutter/webview_flutter.dart';
import 'package:http/http.dart' as http;
import 'package:in_app_update/in_app_update.dart';
import 'package:flutter_spinkit/flutter_spinkit.dart';
import 'package:firebase_core/firebase_core.dart';
import 'dart:convert';
import 'dart:io';
import 'services/notification_service.dart';
import 'pages/settings_page.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  
  // Initialize Firebase (handle errors gracefully)
  try {
    await Firebase.initializeApp();
    debugPrint('Firebase initialized successfully');
  } catch (e) {
    debugPrint('Firebase initialization failed: $e');
    // Continue without Firebase - local notifications will still work
  }
  
  // Initialize notifications
  try {
    await NotificationService().initialize();
    debugPrint('NotificationService initialized successfully');
  } catch (e) {
    debugPrint('NotificationService initialization failed: $e');
  }
  
  SystemChrome.setPreferredOrientations([
    DeviceOrientation.portraitUp,
    DeviceOrientation.portraitDown,
  ]);
  SystemChrome.setSystemUIOverlayStyle(
    const SystemUiOverlayStyle(
      statusBarColor: Colors.transparent,
      statusBarIconBrightness: Brightness.dark,
    ),
  );
  runApp(const NeptunAlarmApp());
}

// Neumorphic кольори
class AppColors {
  static const background = Color(0xFFE0E5EC);
  static const darkShadow = Color(0xFFA3B1C6);
  static const lightShadow = Color(0xFFFFFFFF);
  static const accent = Color(0xFF4A90E2);
  static const accentDark = Color(0xFF2E5C8A);
  static const danger = Color(0xFFE63946);
  static const warning = Color(0xFFFF9500);
  static const success = Color(0xFF30D158);
}

class NeptunAlarmApp extends StatelessWidget {
  const NeptunAlarmApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Dron Alerts',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        fontFamily: 'SF Pro Display',
        scaffoldBackgroundColor: AppColors.background,
        useMaterial3: true,
      ),
      home: const MainPage(),
    );
  }
}

// Neumorphic контейнер
class NeumorphicContainer extends StatelessWidget {
  final Widget child;
  final double borderRadius;
  final EdgeInsets? padding;
  final bool isPressed;
  
  const NeumorphicContainer({
    super.key,
    required this.child,
    this.borderRadius = 20,
    this.padding,
    this.isPressed = false,
  });

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: padding,
      decoration: BoxDecoration(
        color: AppColors.background,
        borderRadius: BorderRadius.circular(borderRadius),
        boxShadow: isPressed
            ? [
                const BoxShadow(
                  color: AppColors.darkShadow,
                  offset: Offset(2, 2),
                  blurRadius: 5,
                  spreadRadius: 1,
                ),
                const BoxShadow(
                  color: AppColors.lightShadow,
                  offset: Offset(-2, -2),
                  blurRadius: 5,
                  spreadRadius: 1,
                ),
              ]
            : [
                const BoxShadow(
                  color: AppColors.darkShadow,
                  offset: Offset(8, 8),
                  blurRadius: 15,
                  spreadRadius: 1,
                ),
                const BoxShadow(
                  color: AppColors.lightShadow,
                  offset: Offset(-8, -8),
                  blurRadius: 15,
                  spreadRadius: 1,
                ),
              ],
      ),
      child: child,
    );
  }
}

class MainPage extends StatefulWidget {
  const MainPage({super.key});

  @override
  State<MainPage> createState() => _MainPageState();
}

class _MainPageState extends State<MainPage> with WidgetsBindingObserver, SingleTickerProviderStateMixin {
  int _selectedIndex = 0;
  late AnimationController _animationController;
  
  final List<Widget> _pages = [
    const MapPage(),
    const MessagesPage(),
    const SettingsPage(),
  ];

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    _animationController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 200),
    );
    _checkForUpdate();
  }

  @override
  void dispose() {
    _animationController.dispose();
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  Future<void> _checkForUpdate() async {
    if (!Platform.isAndroid) return;

    try {
      final updateInfo = await InAppUpdate.checkForUpdate();
      
      if (updateInfo.updateAvailability == UpdateAvailability.updateAvailable) {
        if (updateInfo.immediateUpdateAllowed) {
          await InAppUpdate.performImmediateUpdate();
        } else if (updateInfo.flexibleUpdateAllowed) {
          _showUpdateDialog();
        }
      }
    } catch (e) {
      debugPrint('Error checking for updates: $e');
    }
  }

  void _showUpdateDialog() {
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) => Dialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(30)),
        backgroundColor: AppColors.background,
        elevation: 0,
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: AppColors.background,
                  boxShadow: const [
                    BoxShadow(
                      color: AppColors.darkShadow,
                      offset: Offset(4, 4),
                      blurRadius: 8,
                    ),
                    BoxShadow(
                      color: AppColors.lightShadow,
                      offset: Offset(-4, -4),
                      blurRadius: 8,
                    ),
                  ],
                ),
                child: const Icon(
                  Icons.system_update_rounded,
                  size: 48,
                  color: AppColors.accent,
                ),
              ),
              const SizedBox(height: 24),
              const Text(
                'Нова версія',
                style: TextStyle(
                  fontSize: 24,
                  fontWeight: FontWeight.bold,
                  color: Color(0xFF2D3748),
                ),
              ),
              const SizedBox(height: 12),
              const Text(
                'Доступна нова версія з покращеннями та виправленнями',
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: 15,
                  color: Color(0xFF718096),
                ),
              ),
              const SizedBox(height: 24),
              Row(
                children: [
                  Expanded(
                    child: _NeumorphicButton(
                      onPressed: () => Navigator.pop(context),
                      child: const Text(
                        'Пізніше',
                        style: TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.w600,
                          color: Color(0xFF718096),
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: _NeumorphicButton(
                      onPressed: () async {
                        Navigator.pop(context);
                        try {
                          await InAppUpdate.startFlexibleUpdate();
                          await InAppUpdate.completeFlexibleUpdate();
                        } catch (e) {
                          debugPrint('Error updating: $e');
                        }
                      },
                      isPrimary: true,
                      child: const Text(
                        'Оновити',
                        style: TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.bold,
                          color: Colors.white,
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      body: AnimatedSwitcher(
        duration: const Duration(milliseconds: 300),
        child: _pages[_selectedIndex],
      ),
      bottomNavigationBar: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: NeumorphicContainer(
            borderRadius: 30,
            padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 16),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceAround,
              children: [
                _buildNavItem(Icons.map_rounded, 'Карта', 0),
                _buildNavItem(Icons.notifications_active_rounded, 'Тривоги', 1),
                _buildNavItem(Icons.settings_rounded, 'Налаштування', 2),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildNavItem(IconData icon, String label, int index) {
    final isSelected = _selectedIndex == index;
    
    return GestureDetector(
      onTap: () {
        if (!isSelected) {
          setState(() => _selectedIndex = index);
          _animationController.forward().then((_) => _animationController.reverse());
        }
      },
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
        decoration: BoxDecoration(
          color: isSelected ? AppColors.accent : Colors.transparent,
          borderRadius: BorderRadius.circular(20),
          boxShadow: isSelected
              ? [
                  BoxShadow(
                    color: AppColors.accent.withValues(alpha: 0.3),
                    blurRadius: 8,
                    offset: const Offset(0, 4),
                  ),
                ]
              : null,
        ),
        child: Row(
          children: [
            Icon(
              icon,
              color: isSelected ? Colors.white : const Color(0xFF718096),
              size: 24,
            ),
            if (isSelected) ...[
              const SizedBox(width: 8),
              Text(
                label,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 16,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

// Neumorphic кнопка
class _NeumorphicButton extends StatefulWidget {
  final Widget child;
  final VoidCallback onPressed;
  final bool isPrimary;

  const _NeumorphicButton({
    required this.child,
    required this.onPressed,
    this.isPrimary = false,
  });

  @override
  State<_NeumorphicButton> createState() => _NeumorphicButtonState();
}

class _NeumorphicButtonState extends State<_NeumorphicButton> {
  bool _isPressed = false;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTapDown: (_) => setState(() => _isPressed = true),
      onTapUp: (_) {
        setState(() => _isPressed = false);
        widget.onPressed();
      },
      onTapCancel: () => setState(() => _isPressed = false),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 150),
        padding: const EdgeInsets.symmetric(vertical: 14),
        decoration: BoxDecoration(
          color: widget.isPrimary ? AppColors.accent : AppColors.background,
          borderRadius: BorderRadius.circular(16),
          boxShadow: widget.isPrimary
              ? [
                  BoxShadow(
                    color: AppColors.accent.withValues(alpha: 0.4),
                    blurRadius: _isPressed ? 4 : 10,
                    offset: Offset(0, _isPressed ? 2 : 6),
                  ),
                ]
              : _isPressed
                  ? [
                      const BoxShadow(
                        color: AppColors.darkShadow,
                        offset: Offset(2, 2),
                        blurRadius: 4,
                      ),
                      const BoxShadow(
                        color: AppColors.lightShadow,
                        offset: Offset(-2, -2),
                        blurRadius: 4,
                      ),
                    ]
                  : [
                      const BoxShadow(
                        color: AppColors.darkShadow,
                        offset: Offset(6, 6),
                        blurRadius: 10,
                      ),
                      const BoxShadow(
                        color: AppColors.lightShadow,
                        offset: Offset(-6, -6),
                        blurRadius: 10,
                      ),
                    ],
        ),
        child: Center(child: widget.child),
      ),
    );
  }
}

class MapPage extends StatefulWidget {
  const MapPage({super.key});

  @override
  State<MapPage> createState() => _MapPageState();
}

class _MapPageState extends State<MapPage> {
  late final WebViewController _controller;
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    
    _controller = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setBackgroundColor(AppColors.background)
      ..enableZoom(true)
      ..setNavigationDelegate(
        NavigationDelegate(
          onProgress: (int progress) {
            if (progress == 100 && _isLoading) {
              setState(() => _isLoading = false);
            }
          },
          onPageStarted: (String url) {
            setState(() => _isLoading = true);
          },
          onPageFinished: (String url) {
            setState(() => _isLoading = false);
          },
          onWebResourceError: (WebResourceError error) {
            debugPrint('WebView error: ${error.description}');
          },
        ),
      )
      ..clearCache()
      ..loadRequest(Uri.parse('https://neptun.in.ua/map-only'));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: Column(
          children: [
            // Neumorphic хедер
            Padding(
              padding: const EdgeInsets.all(20),
              child: Row(
                children: [
                  Expanded(
                    child: NeumorphicContainer(
                      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
                      borderRadius: 25,
                      child: Row(
                        children: [
                          Container(
                            padding: const EdgeInsets.all(8),
                            decoration: BoxDecoration(
                              shape: BoxShape.circle,
                              gradient: LinearGradient(
                                colors: [AppColors.accent, AppColors.accentDark],
                                begin: Alignment.topLeft,
                                end: Alignment.bottomRight,
                              ),
                            ),
                            child: const Icon(
                              Icons.map_rounded,
                              color: Colors.white,
                              size: 20,
                            ),
                          ),
                          const SizedBox(width: 12),
                          const Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                '🇺🇦 Карта Тривог',
                                style: TextStyle(
                                  fontSize: 18,
                                  fontWeight: FontWeight.bold,
                                  color: Color(0xFF2D3748),
                                ),
                              ),
                              Text(
                                'Онлайн моніторинг',
                                style: TextStyle(
                                  fontSize: 12,
                                  color: Color(0xFF718096),
                                ),
                              ),
                            ],
                          ),
                          const Spacer(),
                          _NeumorphicIconButton(
                            icon: Icons.refresh_rounded,
                            onPressed: () => _controller.reload(),
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),
            // WebView з Neumorphic контейнером
            Expanded(
              child: Padding(
                padding: const EdgeInsets.fromLTRB(20, 0, 20, 20),
                child: NeumorphicContainer(
                  borderRadius: 30,
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(30),
                    child: Stack(
                      children: [
                        WebViewWidget(controller: _controller),
                        if (_isLoading)
                          Container(
                            color: AppColors.background,
                            child: Center(
                              child: Column(
                                mainAxisAlignment: MainAxisAlignment.center,
                                children: [
                                  SpinKitPulse(
                                    color: AppColors.accent,
                                    size: 60,
                                  ),
                                  const SizedBox(height: 24),
                                  const Text(
                                    'Завантаження карти...',
                                    style: TextStyle(
                                      color: Color(0xFF718096),
                                      fontSize: 16,
                                      fontWeight: FontWeight.w500,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// Neumorphic іконка-кнопка
class _NeumorphicIconButton extends StatefulWidget {
  final IconData icon;
  final VoidCallback onPressed;
  final Color? color;

  const _NeumorphicIconButton({
    required this.icon,
    required this.onPressed,
    this.color,
  });

  @override
  State<_NeumorphicIconButton> createState() => _NeumorphicIconButtonState();
}

class _NeumorphicIconButtonState extends State<_NeumorphicIconButton> {
  bool _isPressed = false;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTapDown: (_) => setState(() => _isPressed = true),
      onTapUp: (_) {
        setState(() => _isPressed = false);
        widget.onPressed();
      },
      onTapCancel: () => setState(() => _isPressed = false),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 150),
        padding: const EdgeInsets.all(10),
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          color: AppColors.background,
          boxShadow: _isPressed
              ? [
                  const BoxShadow(
                    color: AppColors.darkShadow,
                    offset: Offset(2, 2),
                    blurRadius: 4,
                  ),
                  const BoxShadow(
                    color: AppColors.lightShadow,
                    offset: Offset(-2, -2),
                    blurRadius: 4,
                  ),
                ]
              : [
                  const BoxShadow(
                    color: AppColors.darkShadow,
                    offset: Offset(4, 4),
                    blurRadius: 8,
                  ),
                  const BoxShadow(
                    color: AppColors.lightShadow,
                    offset: Offset(-4, -4),
                    blurRadius: 8,
                  ),
                ],
        ),
        child: Icon(
          widget.icon,
          color: widget.color ?? AppColors.accent,
          size: 22,
        ),
      ),
    );
  }
}

class MessagesPage extends StatefulWidget {
  const MessagesPage({super.key});

  @override
  State<MessagesPage> createState() => _MessagesPageState();
}

class _MessagesPageState extends State<MessagesPage> {
  List<AlarmMessage> _messages = [];
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadMessages();
  }

  Future<void> _loadMessages() async {
    try {
      final response = await http.get(Uri.parse('https://neptun.in.ua/api/messages'));
      if (response.statusCode == 200) {
        final data = json.decode(utf8.decode(response.bodyBytes));
        setState(() {
          _messages = (data['messages'] as List)
              .map((m) => AlarmMessage.fromJson(m))
              .toList();
          _isLoading = false;
        });
      }
    } catch (e) {
      debugPrint('Error loading messages: $e');
      setState(() => _isLoading = false);
    }
  }

  IconData _getIconForType(String type) {
    if (type.contains('БпЛА') || type.contains('дрон')) return Icons.airplanemode_active_rounded;
    if (type.contains('ракет')) return Icons.rocket_launch_rounded;
    if (type.contains('артилерії')) return Icons.gps_fixed_rounded;
    if (type.contains('вибух')) return Icons.warning_rounded;
    return Icons.info_outline_rounded;
  }

  LinearGradient _getGradientForType(String type) {
    if (type.contains('БпЛА') || type.contains('дрон')) {
      return const LinearGradient(
        colors: [Color(0xFFFF9500), Color(0xFFFF6B00)],
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
      );
    }
    if (type.contains('ракет')) {
      return const LinearGradient(
        colors: [Color(0xFFE63946), Color(0xFFBE2A35)],
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
      );
    }
    if (type.contains('артилерії')) {
      return const LinearGradient(
        colors: [Color(0xFFFF5722), Color(0xFFD84315)],
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
      );
    }
    if (type.contains('вибух')) {
      return const LinearGradient(
        colors: [Color(0xFFF44336), Color(0xFFD32F2F)],
        begin: Alignment.topLeft,
        end: Alignment.bottomRight,
      );
    }
    return const LinearGradient(
      colors: [Color(0xFF9E9E9E), Color(0xFF757575)],
      begin: Alignment.topLeft,
      end: Alignment.bottomRight,
    );
  }

  Color _getColorForType(String type) {
    if (type.contains('БпЛА') || type.contains('дрон')) return const Color(0xFFFF9500);
    if (type.contains('ракет')) return const Color(0xFFE63946);
    if (type.contains('артилерії')) return const Color(0xFFFF5722);
    if (type.contains('вибух')) return const Color(0xFFF44336);
    return const Color(0xFF9E9E9E);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: AppColors.background,
      body: SafeArea(
        child: Column(
          children: [
            // Neumorphic хедер
            Padding(
              padding: const EdgeInsets.all(20),
              child: Row(
                children: [
                  Expanded(
                    child: NeumorphicContainer(
                      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
                      borderRadius: 25,
                      child: Row(
                        children: [
                          Container(
                            padding: const EdgeInsets.all(8),
                            decoration: BoxDecoration(
                              shape: BoxShape.circle,
                              gradient: const LinearGradient(
                                colors: [AppColors.danger, Color(0xFFBE2A35)],
                                begin: Alignment.topLeft,
                                end: Alignment.bottomRight,
                              ),
                            ),
                            child: const Icon(
                              Icons.notifications_active_rounded,
                              color: Colors.white,
                              size: 20,
                            ),
                          ),
                          const SizedBox(width: 12),
                          Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                '🚨 Тривоги (${_messages.length})',
                                style: const TextStyle(
                                  fontSize: 18,
                                  fontWeight: FontWeight.bold,
                                  color: Color(0xFF2D3748),
                                ),
                              ),
                              const Text(
                                'Актуальні повідомлення',
                                style: TextStyle(
                                  fontSize: 12,
                                  color: Color(0xFF718096),
                                ),
                              ),
                            ],
                          ),
                          const Spacer(),
                          _NeumorphicIconButton(
                            icon: Icons.refresh_rounded,
                            onPressed: () {
                              setState(() => _isLoading = true);
                              _loadMessages();
                            },
                          ),
                        ],
                      ),
                    ),
                  ),
                ],
              ),
            ),
            // Список повідомлень
            Expanded(
              child: _isLoading
                  ? Center(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          SpinKitWave(
                            color: AppColors.accent,
                            size: 40,
                          ),
                          const SizedBox(height: 24),
                          const Text(
                            'Завантаження...',
                            style: TextStyle(
                              color: Color(0xFF718096),
                              fontSize: 16,
                              fontWeight: FontWeight.w500,
                            ),
                          ),
                        ],
                      ),
                    )
                  : _messages.isEmpty
                      ? Center(
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Container(
                                padding: const EdgeInsets.all(20),
                                decoration: BoxDecoration(
                                  shape: BoxShape.circle,
                                  color: AppColors.background,
                                  boxShadow: const [
                                    BoxShadow(
                                      color: AppColors.darkShadow,
                                      offset: Offset(8, 8),
                                      blurRadius: 15,
                                    ),
                                    BoxShadow(
                                      color: AppColors.lightShadow,
                                      offset: Offset(-8, -8),
                                      blurRadius: 15,
                                    ),
                                  ],
                                ),
                                child: const Icon(
                                  Icons.check_circle_rounded,
                                  size: 64,
                                  color: AppColors.success,
                                ),
                              ),
                              const SizedBox(height: 24),
                              const Text(
                                'Немає активних тривог',
                                style: TextStyle(
                                  fontSize: 20,
                                  fontWeight: FontWeight.bold,
                                  color: Color(0xFF2D3748),
                                ),
                              ),
                              const SizedBox(height: 8),
                              const Text(
                                'Все спокійно 🇺🇦',
                                style: TextStyle(
                                  fontSize: 16,
                                  color: Color(0xFF718096),
                                ),
                              ),
                            ],
                          ),
                        )
                      : RefreshIndicator(
                          color: AppColors.accent,
                          onRefresh: _loadMessages,
                          child: ListView.builder(
                            padding: const EdgeInsets.fromLTRB(20, 0, 20, 20),
                            itemCount: _messages.length,
                            itemBuilder: (context, index) {
                              final message = _messages[index];
                              return Padding(
                                padding: const EdgeInsets.only(bottom: 16),
                                child: NeumorphicContainer(
                                  padding: const EdgeInsets.all(16),
                                  borderRadius: 20,
                                  child: Row(
                                    children: [
                                      Container(
                                        padding: const EdgeInsets.all(12),
                                        decoration: BoxDecoration(
                                          borderRadius: BorderRadius.circular(15),
                                          gradient: _getGradientForType(message.type),
                                          boxShadow: [
                                            BoxShadow(
                                              color: _getColorForType(message.type).withValues(alpha: 0.3),
                                              blurRadius: 8,
                                              offset: const Offset(0, 4),
                                            ),
                                          ],
                                        ),
                                        child: Icon(
                                          _getIconForType(message.type),
                                          color: Colors.white,
                                          size: 28,
                                        ),
                                      ),
                                      const SizedBox(width: 16),
                                      Expanded(
                                        child: Column(
                                          crossAxisAlignment: CrossAxisAlignment.start,
                                          children: [
                                            Text(
                                              message.location,
                                              style: const TextStyle(
                                                fontSize: 16,
                                                fontWeight: FontWeight.bold,
                                                color: Color(0xFF2D3748),
                                              ),
                                            ),
                                            const SizedBox(height: 6),
                                            Container(
                                              padding: const EdgeInsets.symmetric(
                                                horizontal: 10,
                                                vertical: 4,
                                              ),
                                              decoration: BoxDecoration(
                                                color: _getColorForType(message.type).withValues(alpha: 0.1),
                                                borderRadius: BorderRadius.circular(8),
                                              ),
                                              child: Text(
                                                message.type,
                                                style: TextStyle(
                                                  fontSize: 12,
                                                  fontWeight: FontWeight.w600,
                                                  color: _getColorForType(message.type),
                                                ),
                                              ),
                                            ),
                                            const SizedBox(height: 8),
                                            Row(
                                              children: [
                                                const Icon(
                                                  Icons.access_time_rounded,
                                                  size: 14,
                                                  color: Color(0xFF718096),
                                                ),
                                                const SizedBox(width: 4),
                                                Text(
                                                  message.timestamp,
                                                  style: const TextStyle(
                                                    fontSize: 12,
                                                    color: Color(0xFF718096),
                                                  ),
                                                ),
                                              ],
                                            ),
                                          ],
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                              );
                            },
                          ),
                        ),
            ),
          ],
        ),
      ),
    );
  }
}

class AlarmMessage {
  final String type;
  final String location;
  final String timestamp;
  final double? latitude;
  final double? longitude;
  final String text;

  AlarmMessage({
    required this.type,
    required this.location,
    required this.timestamp,
    this.latitude,
    this.longitude,
    required this.text,
  });

  factory AlarmMessage.fromJson(Map<String, dynamic> json) {
    return AlarmMessage(
      type: json['type'] ?? 'Невідомо',
      location: json['location'] ?? 'Невідоме місце',
      timestamp: json['timestamp'] ?? '',
      latitude: json['latitude']?.toDouble(),
      longitude: json['longitude']?.toDouble(),
      text: json['text'] ?? '',
    );
  }
}
