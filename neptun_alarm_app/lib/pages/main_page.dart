import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:in_app_update/in_app_update.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:google_mobile_ads/google_mobile_ads.dart';
import 'package:package_info_plus/package_info_plus.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:http/http.dart' as http;
import 'dart:io';
import 'dart:async';
import 'dart:convert';
import '../theme/app_theme.dart';
import '../services/ad_service.dart';
import '../services/purchase_service.dart';
import '../services/notification_service.dart';
import '../main.dart';
import 'native_map_page.dart';
import 'messages_page.dart';
import 'chat_home_page.dart';
import 'safety_page.dart';
import 'aviation_page.dart';
import 'premium_page.dart';
import 'settings_page.dart';
import 'telegram_page.dart';

/// Головна сторінка з покращеною UX структурою:
/// - 3 основні таби внизу (Карта, Тривоги, Чат)
/// - Іконки в header (Settings, Premium, Safety)
/// - Чистий мінімалістичний дизайн
class MainPage extends StatefulWidget {
  const MainPage({super.key});

  @override
  State<MainPage> createState() => MainPageState();
}

class MainPageState extends State<MainPage> with WidgetsBindingObserver {
  int _selectedIndex = 0;
  final AdService _adService = AdService();
  Timer? _bannerCheckTimer;
  
  // Online users
  int _onlineUsers = 0;
  Timer? _onlineTimer;


  // 5 основних сторінок в табах (4 + WebView)
  late final List<Widget> _mainPages;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    
    // Ініціалізація сторінок
    _mainPages = [
      const NativeMapPage(),
      const MessagesPage(),
      const ChatHomePage(),
      const AviationPage(),
      const SafetyPage(),
    ];
    
    _startOnlineTimer();
    PurchaseService().premiumNotifier.addListener(_onPremiumStatusChanged);
    _startBannerCheckTimer();
    
    // Mark session as active after content loads - enables App Open Ads on resume
    Future.delayed(const Duration(seconds: 5), () {
      if (mounted) {
        _adService.markSessionActive();
      }
    });
    
    Future.delayed(const Duration(milliseconds: 100), () async {
      if (mounted) {
        _checkForUpdate();
        await _checkFirstLaunch(); // Welcome (тільки для нових)
      }
    });
  }
  
  void _startOnlineTimer() {
    _loadOnlineCount();
    _onlineTimer = Timer.periodic(
      const Duration(seconds: 30),
      (_) => _loadOnlineCount(),
    );
  }
  
  Future<void> _loadOnlineCount() async {
    if (!mounted) return;
    try {
      final deviceId = NotificationService().deviceId;
      final platform = Platform.isAndroid ? 'android' : 'ios';

      final response = await http.post(
        Uri.parse('https://neptun.in.ua/presence'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'id': deviceId ?? '${platform}_${DateTime.now().millisecondsSinceEpoch}',
          'platform': platform,
        }),
      ).timeout(const Duration(seconds: 10));

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        if (mounted) {
          setState(() => _onlineUsers = data['apps'] ?? 0);
        }
      }
    } catch (e) {
      debugPrint('Error loading online count: $e');
    }
  }
  
  void _toggleTheme() {
    HapticFeedback.lightImpact();
    NeptunAlarmApp.of(context)?.toggleTheme();
  }

  void _startBannerCheckTimer() {
    int attempts = 0;
    _bannerCheckTimer = Timer.periodic(const Duration(seconds: 2), (timer) {
      attempts++;
      debugPrint('🎯 Banner check attempt $attempts: isLoaded=${_adService.isBannerAdLoaded}, bannerAd=${_adService.bannerAd != null}, isPremium=${_adService.debugIsPremium}, rawLoaded=${_adService.debugIsBannerLoaded}, isAdFree=${_adService.debugIsAdFree}');
      if (!mounted || attempts > 15) {
        timer.cancel();
        return;
      }
      if (_adService.isBannerAdLoaded && _adService.bannerAd != null) {
        debugPrint('🎯 Banner found! Calling setState');
        setState(() {});
        timer.cancel();
      }
    });
  }

  void _onPremiumStatusChanged() {
    if (PurchaseService().isPremium && mounted) {
      setState(() {});
      _adService.disposeBannerAd();
    }
  }


  Future<void> _checkFirstLaunch() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final isFirstLaunch = prefs.getBool('first_launch') ?? true;
      final welcomeSkipped = prefs.getBool('welcome_skipped') ?? false;

      if (isFirstLaunch && !welcomeSkipped) {
        await Future.delayed(const Duration(milliseconds: 500));
        if (mounted) {
          _showWelcomeDialog();
          await prefs.setBool('first_launch', false);
        }
      } else if (isFirstLaunch) {
        await prefs.setBool('first_launch', false);
      }
    } catch (e) {
      debugPrint('Error checking first launch: $e');
    }
  }

  void _showWelcomeDialog() {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    showDialog(
      context: context,
      barrierDismissible: true,
      builder: (context) => Dialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        backgroundColor: isDark ? AppColors.darkSurface : AppColors.surface,
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Container(
                width: 72,
                height: 72,
                decoration: BoxDecoration(
                  color: AppColors.primaryLight,
                  borderRadius: BorderRadius.circular(16),
                ),
                child: const Icon(Icons.shield, size: 40, color: AppColors.primary),
              ),
              const SizedBox(height: 20),
              Text(
                'Ласкаво просимо!',
                style: TextStyle(
                  fontSize: 22,
                  fontWeight: FontWeight.w700,
                  color: isDark ? Colors.white : AppColors.textPrimary,
                ),
              ),
              const SizedBox(height: 12),
              Text(
                'Neptun допоможе вам отримувати сповіщення про повітряні тривоги в Україні.',
                textAlign: TextAlign.center,
                style: TextStyle(
                  fontSize: 15,
                  color: isDark ? Colors.grey[400] : AppColors.textSecondary,
                  height: 1.4,
                ),
              ),
              const SizedBox(height: 24),
              SizedBox(
                width: double.infinity,
                child: FilledButton(
                  onPressed: () {
                    Navigator.pop(context);
                    _openSettings();
                  },
                  style: FilledButton.styleFrom(
                    backgroundColor: AppColors.primary,
                    padding: const EdgeInsets.symmetric(vertical: 14),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  ),
                  child: const Text('Налаштувати регіони', style: TextStyle(fontSize: 16)),
                ),
              ),
              const SizedBox(height: 12),
              TextButton(
                onPressed: () async {
                  final prefs = await SharedPreferences.getInstance();
                  await prefs.setBool('welcome_skipped', true);
                  if (context.mounted) Navigator.pop(context);
                },
                child: Text(
                  'Пропустити',
                  style: TextStyle(color: isDark ? Colors.grey[400] : AppColors.textSecondary),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  @override
  void dispose() {
    _bannerCheckTimer?.cancel();
    _onlineTimer?.cancel();
    _adService.disposeBannerAd();
    PurchaseService().premiumNotifier.removeListener(_onPremiumStatusChanged);
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  // Публічний метод для переключення табів (використовується з інших сторінок)
  void switchToTab(int index) {
    if (index >= 0 && index < _mainPages.length && mounted) {
      setState(() => _selectedIndex = index);
      HapticFeedback.lightImpact();
      
    }
  }

  Future<void> _checkForUpdate() async {
    try {
      if (Platform.isAndroid) {
        // Android: Use in_app_update
        final updateInfo = await InAppUpdate.checkForUpdate();
        if (updateInfo.updateAvailability == UpdateAvailability.updateAvailable) {
          if (updateInfo.immediateUpdateAllowed) {
            await InAppUpdate.performImmediateUpdate();
          } else if (updateInfo.flexibleUpdateAllowed) {
            _showUpdateSnackBar();
          }
        }
      } else if (Platform.isIOS) {
        // iOS: Check App Store version via iTunes API
        await _checkiOSUpdate();
      }
    } catch (e) {
      debugPrint('Error checking for updates: $e');
    }
  }

  /// Check for iOS update via iTunes Lookup API
  Future<void> _checkiOSUpdate() async {
    try {
      // Don't show update dialog too often (once per day)
      final prefs = await SharedPreferences.getInstance();
      final lastCheck = prefs.getInt('ios_update_last_check') ?? 0;
      final now = DateTime.now().millisecondsSinceEpoch;
      if (now - lastCheck < 24 * 60 * 60 * 1000) {
        debugPrint('iOS update check skipped (checked within 24h)');
        return;
      }
      
      // Get current app version
      final packageInfo = await PackageInfo.fromPlatform();
      final currentVersion = packageInfo.version;
      
      // Query App Store for latest version
      // Bundle ID: com.neptunalarm.neptunAlarmApp
      const bundleId = 'com.neptunalarm.neptunAlarmApp';
      final response = await http.get(
        Uri.parse('https://itunes.apple.com/lookup?bundleId=$bundleId&country=ua'),
      );
      
      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        if (data['resultCount'] > 0) {
          final storeVersion = data['results'][0]['version'] as String;
          final storeUrl = data['results'][0]['trackViewUrl'] as String;
          
          debugPrint('iOS version check: current=$currentVersion, store=$storeVersion');
          
          if (_isNewerVersion(storeVersion, currentVersion)) {
            await prefs.setInt('ios_update_last_check', now);
            if (mounted) {
              _showIOSUpdateDialog(storeVersion, storeUrl);
            }
          }
        }
      }
    } catch (e) {
      debugPrint('Error checking iOS update: $e');
    }
  }

  /// Compare version strings (e.g., "1.6.9" > "1.6.8")
  bool _isNewerVersion(String storeVersion, String currentVersion) {
    try {
      final storeParts = storeVersion.split('.').map(int.parse).toList();
      final currentParts = currentVersion.split('.').map(int.parse).toList();
      
      for (int i = 0; i < storeParts.length && i < currentParts.length; i++) {
        if (storeParts[i] > currentParts[i]) return true;
        if (storeParts[i] < currentParts[i]) return false;
      }
      return storeParts.length > currentParts.length;
    } catch (e) {
      return false;
    }
  }

  /// Show iOS update dialog
  void _showIOSUpdateDialog(String newVersion, String storeUrl) {
    showDialog(
      context: context,
      barrierDismissible: true,
      builder: (ctx) => AlertDialog(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
        title: Row(
          children: [
            Icon(Icons.system_update, color: Theme.of(context).primaryColor),
            const SizedBox(width: 12),
            const Text('Нова версія'),
          ],
        ),
        content: Text(
          'Доступна нова версія $newVersion\n\nОновіть додаток для отримання нових функцій та виправлень.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Пізніше'),
          ),
          ElevatedButton(
            onPressed: () {
              Navigator.pop(ctx);
              launchUrl(Uri.parse(storeUrl), mode: LaunchMode.externalApplication);
            },
            child: const Text('Оновити'),
          ),
        ],
      ),
    );
  }

  void _showUpdateSnackBar() {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: const Text('Доступне оновлення'),
        action: SnackBarAction(
          label: 'Оновити',
          onPressed: () => InAppUpdate.performImmediateUpdate(),
        ),
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
      ),
    );
  }

  // Відкрити Settings як окремий екран
  void _openSettings() {
    Navigator.push(
      context,
      MaterialPageRoute(builder: (context) => const SettingsPage()),
    );
  }

  // Відкрити Premium як окремий екран
  void _openPremium() {
    Navigator.push(
      context,
      MaterialPageRoute(builder: (context) => const PremiumPage()),
    );
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final isPremium = PurchaseService().isPremium;
    
    return PopScope(
      canPop: _selectedIndex == 0,
      onPopInvokedWithResult: (didPop, result) {
        if (!didPop && _selectedIndex != 0) {
          setState(() => _selectedIndex = 0);
        }
      },
      child: Scaffold(
      body: SafeArea(
        bottom: false,
        child: Column(
          children: [
            // 🔝 HEADER - мінімалістичний стиль
            _buildKyivHeader(isDark, isPremium),
            
            // 📱 MAIN CONTENT
            Expanded(
              child: IndexedStack(
                index: _selectedIndex,
                children: _mainPages,
              ),
            ),
          ],
        ),
      ),
      // 📊 BOTTOM NAV + AD BANNER
      bottomNavigationBar: _buildKyivBottomNav(isDark),
    ),
    );
  }

  /// Київ Цифровий Header - компактний
  Widget _buildKyivHeader(bool isDark, bool isPremium) {
    // Для світлої теми використовуємо більш контрастні кольори
    final containerBg = isDark 
        ? AppColors.darkSurface
        : AppColors.surface;
    final dividerColor = isDark
        ? AppColors.darkDivider
        : AppColors.divider;
    final iconColor = isDark ? Colors.white : AppColors.textPrimary;
    
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      child: Row(
        children: [
          // 🔹 ЛІВА ГРУПА: Online + Theme
          Container(
            height: 42,
            decoration: BoxDecoration(
              color: containerBg,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(
                color: dividerColor,
                width: 1,
              ),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                // Online indicator
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12),
                  decoration: BoxDecoration(
                    color: isDark ? AppColors.darkCard : AppColors.kyivGray,
                    borderRadius: const BorderRadius.horizontal(left: Radius.circular(11)),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Container(
                        width: 8,
                        height: 8,
                        decoration: BoxDecoration(
                          color: _onlineUsers > 0 ? AppColors.kyivGreen : Colors.grey,
                          shape: BoxShape.circle,
                          boxShadow: _onlineUsers > 0 ? [
                            BoxShadow(
                              color: AppColors.kyivGreen.withValues(alpha: 0.5),
                              blurRadius: 6,
                            ),
                          ] : null,
                        ),
                      ),
                      const SizedBox(width: 6),
                      Text(
                        _onlineUsers > 0 ? '$_onlineUsers' : '...',
                        style: TextStyle(
                          fontSize: 13,
                          fontWeight: FontWeight.w600,
                          color: _onlineUsers > 0 
                              ? AppColors.kyivGreen
                              : (isDark ? Colors.white70 : AppColors.textSecondary),
                        ),
                      ),
                    ],
                  ),
                ),
                // Роздільник
                Container(width: 1, color: dividerColor),
                // Theme toggle
                GestureDetector(
                  onTap: () {
                    HapticFeedback.lightImpact();
                    _toggleTheme();
                  },
                  child: Container(
                    width: 42,
                    decoration: const BoxDecoration(
                      borderRadius: BorderRadius.horizontal(right: Radius.circular(11)),
                    ),
                    child: Center(
                      child: Icon(
                        isDark ? Icons.light_mode_rounded : Icons.dark_mode_rounded,
                        color: isDark ? Colors.amber : iconColor,
                        size: 20,
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
          
          const Spacer(),
          
          // 🔹 ПРАВА ГРУПА: Premium + Telegram + Settings
          Container(
            height: 42,
            decoration: BoxDecoration(
              color: containerBg,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(
                color: dividerColor,
                width: 1,
              ),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                // Premium button (якщо не преміум)
                if (!isPremium) ...[
                  GestureDetector(
                    onTap: () {
                      HapticFeedback.lightImpact();
                      _openPremium();
                    },
                    child: Container(
                      padding: const EdgeInsets.symmetric(horizontal: 12),
                      decoration: BoxDecoration(
                        color: isDark ? AppColors.darkCard : AppColors.kyivGray,
                        borderRadius: const BorderRadius.horizontal(left: Radius.circular(11)),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          const Icon(Icons.workspace_premium, color: Colors.amber, size: 18),
                          const SizedBox(width: 4),
                          const Text(
                            'PRO',
                            style: TextStyle(
                              fontSize: 12,
                              fontWeight: FontWeight.w700,
                              color: Colors.amber,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                  Container(width: 1, color: dividerColor),
                ],
                // Telegram button
                GestureDetector(
                  onTap: () {
                    HapticFeedback.lightImpact();
                    Navigator.push(
                      context,
                      MaterialPageRoute(builder: (context) => const TelegramPage()),
                    );
                  },
                  child: Container(
                    width: 42,
                    decoration: BoxDecoration(
                      color: isDark
                          ? const Color(0xFF0088CC).withValues(alpha: 0.2)
                          : const Color(0xFF0088CC).withValues(alpha: 0.12),
                      borderRadius: isPremium 
                          ? const BorderRadius.horizontal(left: Radius.circular(11))
                          : BorderRadius.zero,
                    ),
                    child: Center(
                      child: Icon(
                        Icons.telegram, 
                        color: isDark ? const Color(0xFF0088CC) : AppColors.textPrimary,
                        size: 20,
                      ),
                    ),
                  ),
                ),
                // Роздільник
                Container(width: 1, color: dividerColor),
                // Settings button
                GestureDetector(
                  onTap: () {
                    HapticFeedback.lightImpact();
                    _openSettings();
                  },
                  child: Container(
                    width: 42,
                    decoration: const BoxDecoration(
                      borderRadius: BorderRadius.horizontal(right: Radius.circular(11)),
                    ),
                    child: Center(
                      child: Icon(Icons.settings_outlined, color: iconColor, size: 20),
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

  /// Київ Цифровий Bottom Navigation
  Widget _buildKyivBottomNav(bool isDark) {
    final bgColor = isDark ? AppColors.darkSurface : AppColors.surface;
    final shadowColor = isDark ? Colors.black : Colors.grey;
    
    return Container(
      decoration: BoxDecoration(
        color: bgColor,
        borderRadius: const BorderRadius.only(
          topLeft: Radius.circular(24),
          topRight: Radius.circular(24),
        ),
        boxShadow: [
          BoxShadow(
            color: shadowColor.withValues(alpha: 0.08),
            blurRadius: 16,
            offset: const Offset(0, -2),
          ),
        ],
      ),
      child: SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            // Ad Banner
            if (_adService.isBannerAdLoaded && _adService.bannerAd != null)
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(12),
                  child: SizedBox(
                    width: _adService.bannerAd!.size.width.toDouble(),
                    height: _adService.bannerAd!.size.height.toDouble(),
                    child: AdWidget(
                      key: ValueKey(_adService.bannerAd!.hashCode),
                      ad: _adService.bannerAd!,
                    ),
                  ),
                ),
              ),
            // Navigation
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.spaceAround,
                children: [
                  _buildKyivNavItem(
                    icon: Icons.map_outlined,
                    activeIcon: Icons.map,
                    label: 'Карта',
                    index: 0,
                    isDark: isDark,
                  ),
                  _buildKyivNavItem(
                    icon: Icons.notifications_outlined,
                    activeIcon: Icons.notifications,
                    label: 'Тривоги',
                    index: 1,
                    isDark: isDark,
                    showBadge: true,
                  ),
                  _buildKyivNavItem(
                    icon: Icons.chat_bubble_outline,
                    activeIcon: Icons.chat_bubble,
                    label: 'Чат',
                    index: 2,
                    isDark: isDark,
                  ),
                  _buildKyivNavItem(
                    icon: Icons.flight_takeoff_outlined,
                    activeIcon: Icons.flight_takeoff,
                    label: 'Авіація',
                    index: 3,
                    isDark: isDark,
                  ),
                  _buildKyivNavItem(
                    icon: Icons.shield_outlined,
                    activeIcon: Icons.shield,
                    label: 'Безпека',
                    index: 4,
                    isDark: isDark,
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
  
  Widget _buildKyivNavItem({
    required IconData icon,
    required IconData activeIcon,
    required String label,
    required int index,
    required bool isDark,
    bool showBadge = false,
  }) {
    final isSelected = _selectedIndex == index;
    final activeColor = isDark ? Colors.white : AppColors.kyivBlue;
    final inactiveColor = isDark ? Colors.grey[500] : AppColors.kyivTextGray;
    
    return Expanded(
      child: GestureDetector(
        onTap: () {
          if (!isSelected) {
            HapticFeedback.lightImpact();
            setState(() => _selectedIndex = index);
          }
        },
        behavior: HitTestBehavior.opaque,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Stack(
              clipBehavior: Clip.none,
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                  decoration: BoxDecoration(
                    color: isSelected 
                        ? activeColor.withValues(alpha: 0.15)
                        : Colors.transparent,
                    borderRadius: BorderRadius.circular(16),
                  ),
                  child: Icon(
                    isSelected ? activeIcon : icon,
                    color: isSelected ? activeColor : inactiveColor,
                    size: 24,
                  ),
                ),
                if (showBadge && index == 1)
                  Positioned(
                    right: 8,
                    top: 4,
                    child: Container(
                      width: 10,
                      height: 10,
                      decoration: BoxDecoration(
                        color: AppColors.kyivRed,
                        shape: BoxShape.circle,
                        border: Border.all(
                          color: isDark ? const Color(0xFF121212) : Colors.white,
                          width: 2,
                        ),
                      ),
                    ),
                  ),
              ],
            ),
            const SizedBox(height: 4),
            Text(
              label,
              style: TextStyle(
                fontSize: 11,
                fontWeight: isSelected ? FontWeight.w600 : FontWeight.w500,
                color: isSelected ? activeColor : inactiveColor,
              ),
            ),
          ],
        ),
      ),
    );
  }

}
