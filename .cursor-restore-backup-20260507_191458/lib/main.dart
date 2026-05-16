import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:flutter/services.dart';
import 'package:firebase_core/firebase_core.dart';
import 'dart:math' as math;
import 'package:firebase_analytics/firebase_analytics.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'dart:io';

import 'theme/app_theme.dart';
import 'core/router/app_router.dart';
import 'services/notification_service.dart';
import 'services/chat_service.dart';
import 'package:app_tracking_transparency/app_tracking_transparency.dart';
import 'services/ad_service.dart';
import 'services/purchase_service.dart';
import 'services/auth_service.dart';
import 'services/tts_service.dart';
import 'services/review_service.dart';
import 'services/alarm_tracking_service.dart';
import 'services/data_stream_service.dart';
import 'services/ios_platform_service.dart';
import 'services/android_platform_service.dart';
import 'dart:async';
import 'services/widget_service.dart';
import 'services/map_ready_notifier.dart';
import 'core/di/service_locator.dart';
import 'core/error/error_handler.dart';
import 'core/providers/providers.dart';
import 'services/briefing_service.dart';
import 'services/map_data_service.dart';

// --- Initialization Logic ---

void main() async {
  // Global framework error handler to prevent Grey Screens of Death
  FlutterError.onError = (FlutterErrorDetails details) {
    // Suppress webview_flutter_wkwebview Pigeon null-assertion noise (iOS edge cases)
    final combined = '${details.exception}${details.stack}';
    if (combined.contains('web_kit.g.dart')) {
      if (kDebugMode) {
        debugPrint(
          '⚠️ webview_flutter_wkwebview Pigeon assertion (known issue, ignored)',
        );
      }
      return;
    }
    debugPrint('🛑 FLUTTER FRAMEWORK ERROR: ${details.exception}');
    if (kDebugMode) {
      debugPrintStack(stackTrace: details.stack);
    }
    // Non-critical errors are swallowed to preserve UI state where possible.
  };

  runZonedGuarded(
    () async {
      WidgetsFlutterBinding.ensureInitialized();

      // Must be set before any font access; false blocks when fonts aren't bundled
      GoogleFonts.config.allowRuntimeFetching = true;

      // Дозволяємо альбомний режим — зручно для карти на планшеті
      await SystemChrome.setPreferredOrientations([
        DeviceOrientation.portraitUp,
        DeviceOrientation.portraitDown,
        DeviceOrientation.landscapeLeft,
        DeviceOrientation.landscapeRight,
      ]);

      // Minimal init before first frame — defer heavy work to avoid splash freeze
      await initServiceLocator();
      await AuthService.initProbe();

      if (Platform.isIOS) {
        await _initializeiOS();
        await _requestATTForIOS();
      } else if (Platform.isAndroid) {
        await _initializeAndroid();
      }

      FirebaseMessaging.onBackgroundMessage(firebaseMessagingBackgroundHandler);
      debugPrint('✅ onBackgroundMessage registered');

      final appRouter = AppRouter(prefs: sl<SharedPreferences>());
      final router = appRouter.router;
      sl.registerSingleton<GoRouter>(router);

      runApp(ProviderScope(child: NeptunAlarmApp(router: appRouter.router)));

      // Defer Sentry & FCM logging so first frame renders immediately
      _deferredInit();
      _initializeServicesInBackground();
    },
    (error, stackTrace) {
      debugPrint('🛑 DART ASYNC ERROR CAUGHT: $error');
      ErrorHandler.captureException(
        error,
        stackTrace: stackTrace,
        context: 'runZonedGuarded',
      );
      if (kDebugMode) {
        debugPrintStack(stackTrace: stackTrace);
      }
    },
  );
}

Future<void> _initializeiOS() async {
  try {
    // Firebase is already initialized in AppDelegate.swift for iOS push notifications
    await Firebase.initializeApp();

    final analytics = FirebaseAnalytics.instance;
    await analytics.setAnalyticsCollectionEnabled(true);

    IOSPlatformService().initialize();

    debugPrint('✅ iOS initialization complete');
  } catch (e) {
    debugPrint('❌ iOS initialization error: $e');
  }
}

/// Request App Tracking Transparency BEFORE any ad/tracking data is collected.
/// Must run before AdService.initialize() — called from main() before runApp().
Future<void> _requestATTForIOS() async {
  try {
    var status = await AppTrackingTransparency.trackingAuthorizationStatus;
    debugPrint('ATT status at launch: $status');

    if (status == TrackingStatus.notDetermined) {
      // Brief delay so system can present the dialog properly (Apple recommendation)
      await Future.delayed(const Duration(milliseconds: 500));
      status = await AppTrackingTransparency.requestTrackingAuthorization();
      debugPrint('ATT permission result: $status');
    }

    // Notify AdService of the result (it will read status when initializing)
    AdService().setATTStatus(status);
  } catch (e) {
    debugPrint('ATT request error: $e');
  }
}

Future<void> _initializeAndroid() async {
  await Future.wait([_initFirebase(), _initAdMobSdk()]);

  await AndroidPlatformService().initialize();

  final androidService = AndroidPlatformService();
  if (androidService.needsBatteryOptimizationWarning) {
    final isBatteryOptDisabled = await androidService
        .isBatteryOptimizationDisabled();
    if (!isBatteryOptDisabled) {
      debugPrint(
        '⚠️ Battery optimization is enabled - notifications may be delayed',
      );
    }
  }

  debugPrint('✅ Android initialization complete');
}

Future<void> _initFirebase() async {
  try {
    await Firebase.initializeApp();
    final analytics = FirebaseAnalytics.instance;
    await analytics.setAnalyticsCollectionEnabled(true);
    debugPrint('Firebase & Analytics initialized successfully');
  } catch (e) {
    debugPrint('Firebase initialization failed: $e');
  }
}

Future<void> _initAdMobSdk() async {
  debugPrint('AdMob SDK will be initialized by AdService');
}

/// Run after first frame — avoids blocking splash
Future<void> _deferredInit() async {
  await ErrorHandler.initialize(
    dsn: const String.fromEnvironment('SENTRY_DSN', defaultValue: ''),
  );

  // Sentry replaces FlutterError.onError — wrap its handler with our filter
  final sentryHandler = FlutterError.onError;
  FlutterError.onError = (FlutterErrorDetails details) {
    final combined = '${details.exception}${details.stack}';
    if (combined.contains('web_kit.g.dart')) {
      if (kDebugMode) {
        debugPrint('⚠️ webview Pigeon assertion (ignored)');
      }
      return;
    }
    sentryHandler?.call(details);
  };

  await _logFcmDebugInfo();
}

/// Log FCM and APNS tokens for debugging push notification issues
Future<void> _logFcmDebugInfo() async {
  try {
    final messaging = FirebaseMessaging.instance;

    // On iOS, APNS token must be available for FCM topics to work
    if (Platform.isIOS) {
      final apnsToken = await messaging.getAPNSToken();
      if (kDebugMode) {
        debugPrint(
          '🍎 APNS token: ${apnsToken != null ? "${apnsToken.substring(0, math.min(20, apnsToken.length))}..." : "NULL ⚠️ (topics will not work!)"}',
        );
      }
      // Don't call getToken() if APNS isn't ready — it throws on iOS
      if (apnsToken == null) {
        return;
      }
    }

    final fcmToken = await messaging.getToken();
    if (kDebugMode) {
      debugPrint(
        '🔑 FCM token: ${fcmToken != null ? "${fcmToken.substring(0, math.min(20, fcmToken.length))}..." : "NULL ⚠️"}',
      );
    }
  } catch (e) {
    debugPrint('⚠️ FCM debug info error: $e');
  }
}

Future<void> _initializeServicesInBackground() async {
  // Initialize PurchaseService and NotificationService in parallel
  // (don't block notifications waiting for purchases)
  if (Platform.isAndroid) {
    await Future.wait([_initPurchaseService(), _initNotificationService()]);
    _initAdService();
    _initWidgetService();
    _initReviewService();
  } else if (Platform.isIOS) {
    await Future.wait([
      _initPurchaseService(),
      _initAdService(),
      _initNotificationService(),
    ]);
    _initWidgetService();
    _initReviewService();
  }

  _initTtsService();

  // Chat service init (device ID, nickname)
  await sl<ChatService>().init();

  // Prefetch map + briefing data to warm caches (deferred, non-blocking)
  unawaited(
    Future.delayed(const Duration(seconds: 3), () async {
      try {
        await Future.wait([
          sl<MapDataService>().fetchAlarms(),
          BriefingService().fetchBriefing(),
        ]);
      } catch (_) {}
    }),
  );
}

Future<void> _initPurchaseService() async {
  try {
    await PurchaseService().initialize();
    // Debug premium disabled — test non-premium flow on emulator
    debugPrint('PurchaseService initialized');
  } catch (e) {
    debugPrint('PurchaseService failed: $e');
  }
}

Future<void> _initAdService() async {
  try {
    await AdService().initialize();
    debugPrint('AdMob initialized');
  } catch (e) {
    debugPrint('AdMob failed: $e');
  }
}

Future<void> _initNotificationService() async {
  try {
    await NotificationService().initialize();
    debugPrint('NotificationService initialized');
    AlarmTrackingService().startTracking();
    debugPrint('AlarmTrackingService started');
  } catch (e) {
    debugPrint('NotificationService failed: $e');
  }
}

Future<void> _initTtsService() async {
  try {
    await TtsService().initialize();
    debugPrint('TtsService initialized');
  } catch (e) {
    debugPrint('TtsService failed: $e');
  }
}

Future<void> _initReviewService() async {
  try {
    await ReviewService().trackAppOpen();
    debugPrint('ReviewService tracked app open');
  } catch (e) {
    debugPrint('ReviewService failed: $e');
  }
}

Future<void> _initWidgetService() async {
  try {
    await WidgetService().initialize();
    debugPrint('WidgetService initialized');
  } catch (e) {
    debugPrint('WidgetService failed: $e');
  }
}

// --- Main App Widget ---

class NeptunAlarmApp extends ConsumerStatefulWidget {
  final GoRouter router;
  const NeptunAlarmApp({super.key, required this.router});

  @override
  ConsumerState<NeptunAlarmApp> createState() => _NeptunAlarmAppState();
}

class _NeptunAlarmAppState extends ConsumerState<NeptunAlarmApp>
    with WidgetsBindingObserver {
  bool _showSplash = true; // splash widget is in the tree
  double _splashOpacity = 1.0; // controls fade-out animation
  bool _minTimeElapsed = false;
  bool _mapReady = false;
  bool _checkedOnboardingDismiss = false;
  DateTime? _lastBackgroundedAt;

  static const _minSplashDuration = Duration(milliseconds: 1500);
  static const _maxSplashDuration = Duration(seconds: 8);
  static const _fadeOutDuration = Duration(milliseconds: 400);

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);

    // Minimum display time so splash animation plays fully
    Future.delayed(_minSplashDuration, () {
      if (mounted) {
        _minTimeElapsed = true;
        _tryDismissSplash();
      }
    });

    // Maximum timeout — dismiss no matter what after 8s
    Future.delayed(_maxSplashDuration, () {
      if (mounted && _showSplash) {
        debugPrint('⏱️ Splash max timeout reached — forcing dismiss');
        _startFadeOut();
      }
    });

    // Listen to map ready signal
    MapReadyNotifier.instance.addListener(_onMapReady);
  }

  void _onMapReady() {
    if (MapReadyNotifier.instance.value && mounted) {
      _mapReady = true;
      _tryDismissSplash();
    }
  }

  void _tryDismissSplash() {
    if (_minTimeElapsed && _mapReady && _showSplash && mounted) {
      debugPrint('✅ Splash dismissed — map ready + min time elapsed');
      _startFadeOut();
    }
  }

  void _checkOnboardingSplashDismiss() {
    if (!_minTimeElapsed ||
        !_showSplash ||
        !mounted ||
        _checkedOnboardingDismiss) {
      return;
    }
    _checkedOnboardingDismiss = true;
    final router = widget.router;
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted || !_showSplash) return;
      try {
        final path = router.routerDelegate.currentConfiguration.fullPath;
        if (path == '/onboarding') {
          debugPrint('✅ Splash dismissed — user on onboarding');
          _startFadeOut();
        }
      } catch (_) {}
    });
  }

  void _startFadeOut() {
    if (!_showSplash) return;
    // Trigger fade-out animation
    setState(() => _splashOpacity = 0.0);
    // Remove widget from tree after animation completes
    Future.delayed(_fadeOutDuration + const Duration(milliseconds: 50), () {
      if (mounted) setState(() => _showSplash = false);
    });
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.paused ||
        state == AppLifecycleState.inactive) {
      _lastBackgroundedAt = DateTime.now();
    } else if (state == AppLifecycleState.resumed &&
        _lastBackgroundedAt != null) {
      final bgDuration = DateTime.now().difference(_lastBackgroundedAt!);
      if (bgDuration >= const Duration(seconds: 5)) {
        DataStreamService.instance.forceReconnectIfNeeded();
        NotificationService().reRegisterOnResume();
      }
      _lastBackgroundedAt = null;
    }
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    MapReadyNotifier.instance.removeListener(_onMapReady);
    super.dispose();
  }

  void _updateSystemUI(bool isDark) {
    SystemChrome.setSystemUIOverlayStyle(
      SystemUiOverlayStyle(
        statusBarColor: Colors.transparent,
        statusBarIconBrightness: isDark ? Brightness.light : Brightness.dark,
        systemNavigationBarColor: isDark
            ? const Color(0xFF0C0C12)
            : const Color(0xFFF8FAFC),
        systemNavigationBarIconBrightness: isDark
            ? Brightness.light
            : Brightness.dark,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final themeMode = ref.watch(themeModeProvider);
    ref.listen<ThemeMode>(themeModeProvider, (previous, next) {
      _updateSystemUI(next == ThemeMode.dark);
    });
    _updateSystemUI(themeMode == ThemeMode.dark);
    _checkOnboardingSplashDismiss();

    return MaterialApp.router(
      title: 'Neptun',
      debugShowCheckedModeBanner: false,
      themeMode: themeMode,
      theme: AppTheme.light,
      darkTheme: AppTheme.dark,
      themeAnimationDuration: const Duration(milliseconds: 450),
      themeAnimationCurve: Curves.easeInOutCubic,
      routerConfig: widget.router,
      builder: (context, child) {
        return Stack(
          fit: StackFit.expand,
          children: [
            child ?? const SizedBox.shrink(),
            if (_showSplash)
              IgnorePointer(
                ignoring: _splashOpacity < 1.0,
                child: AnimatedOpacity(
                  opacity: _splashOpacity,
                  duration: _fadeOutDuration,
                  curve: Curves.easeOut,
                  child: const _SplashScreen(),
                ),
              ),
          ],
        );
      },
    );
  }
}

// ===== ANIMATED SPLASH SCREEN =====
class _SplashScreen extends StatefulWidget {
  const _SplashScreen();

  @override
  State<_SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<_SplashScreen>
    with TickerProviderStateMixin {
  late AnimationController _mainController;
  late AnimationController _pulseController;
  late AnimationController _shimmerController;
  late Animation<double> _scaleAnimation;
  late Animation<double> _opacityAnimation;
  late Animation<double> _slideAnimation;
  late Animation<double> _pulseAnimation;
  late Animation<double> _ringAnimation;
  late Animation<double> _shimmerAnimation;

  @override
  void initState() {
    super.initState();
    _mainController = AnimationController(
      duration: const Duration(milliseconds: 1200),
      vsync: this,
    )..forward();

    _pulseController = AnimationController(
      duration: const Duration(milliseconds: 2000),
      vsync: this,
    )..forward();

    _shimmerController = AnimationController(
      duration: const Duration(milliseconds: 1500),
      vsync: this,
    )..repeat();

    _scaleAnimation = Tween<double>(begin: 0.3, end: 1.0).animate(
      CurvedAnimation(parent: _mainController, curve: Curves.elasticOut),
    );
    _opacityAnimation = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(
        parent: _mainController,
        curve: const Interval(0.0, 0.4, curve: Curves.easeOut),
      ),
    );
    _slideAnimation = Tween<double>(begin: 30.0, end: 0.0).animate(
      CurvedAnimation(
        parent: _mainController,
        curve: const Interval(0.2, 0.7, curve: Curves.easeOutCubic),
      ),
    );
    _pulseAnimation = Tween<double>(begin: 1.0, end: 1.08).animate(
      CurvedAnimation(parent: _pulseController, curve: Curves.easeInOut),
    );
    _ringAnimation = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(parent: _pulseController, curve: Curves.easeInOut),
    );
    _shimmerAnimation = Tween<double>(begin: -1.0, end: 2.0).animate(
      CurvedAnimation(parent: _shimmerController, curve: Curves.linear),
    );
  }

  @override
  void dispose() {
    _mainController.dispose();
    _pulseController.dispose();
    _shimmerController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final cs = Theme.of(context).colorScheme;

    // Theme-aware colors (Design 4.0)
    final bgGradient = isDark
        ? const [Color(0xFF0C0C12), Color(0xFF0E0E18), Color(0xFF12121A)]
        : const [Color(0xFFF0F9FF), Color(0xFFF0FDFA), Color(0xFFF8FAFC)];
    final accentColor = cs.primary;
    final accentGlow = isDark
        ? cs.primary.withValues(alpha: 0.4)
        : cs.primary.withValues(alpha: 0.2);
    final subtitleColor = isDark
        ? const Color(0xFF7D8DA1)
        : const Color(0xFF64748B);
    return Scaffold(
      body: AnimatedBuilder(
        animation: Listenable.merge([_mainController, _pulseController]),
        builder: (context, _) {
          return Container(
            width: double.infinity,
            height: double.infinity,
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: bgGradient,
              ),
            ),
            child: Stack(
              children: [
                // Radial glow behind logo
                Center(
                  child: Transform.scale(
                    scale: 1.0 + (_ringAnimation.value * 0.3),
                    child: Container(
                      width: 200,
                      height: 200,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        gradient: RadialGradient(
                          colors: [
                            accentGlow.withValues(
                              alpha: 0.15 * (1 - _ringAnimation.value),
                            ),
                            accentGlow.withValues(
                              alpha: 0.05 * (1 - _ringAnimation.value),
                            ),
                            Colors.transparent,
                          ],
                        ),
                      ),
                    ),
                  ),
                ),

                // Main content
                Center(
                  child: Opacity(
                    opacity: _opacityAnimation.value,
                    child: Transform.scale(
                      scale: _scaleAnimation.value,
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          // Logo with pulse + glow ring
                          Transform.scale(
                            scale: _pulseAnimation.value,
                            child: Stack(
                              alignment: Alignment.center,
                              children: [
                                // Outer glow ring
                                Container(
                                  width: 136,
                                  height: 136,
                                  decoration: BoxDecoration(
                                    borderRadius: BorderRadius.circular(38),
                                    border: Border.all(
                                      color: accentColor.withValues(
                                        alpha:
                                            0.15 +
                                            (_ringAnimation.value * 0.15),
                                      ),
                                      width: 1.5,
                                    ),
                                  ),
                                ),
                                // Main icon container
                                Container(
                                  width: 120,
                                  height: 120,
                                  decoration: BoxDecoration(
                                    gradient: LinearGradient(
                                      colors: [
                                        accentColor,
                                        accentColor.withValues(alpha: 0.85),
                                        isDark
                                            ? const Color(0xFF1E40AF)
                                            : const Color(0xFF2563EB),
                                      ],
                                      begin: Alignment.topLeft,
                                      end: Alignment.bottomRight,
                                    ),
                                    borderRadius: BorderRadius.circular(32),
                                    boxShadow: [
                                      BoxShadow(
                                        color: accentColor.withValues(
                                          alpha: 0.4,
                                        ),
                                        blurRadius: 32,
                                        spreadRadius: 2,
                                      ),
                                      BoxShadow(
                                        color: accentColor.withValues(
                                          alpha: 0.15,
                                        ),
                                        blurRadius: 60,
                                        spreadRadius: 8,
                                      ),
                                    ],
                                  ),
                                  child: const Icon(
                                    Icons.shield_rounded,
                                    size: 56,
                                    color: Colors.white,
                                  ),
                                ),
                              ],
                            ),
                          ),
                          const SizedBox(height: 32),

                          // App name with gradient text
                          Transform.translate(
                            offset: Offset(0, _slideAnimation.value),
                            child: ShaderMask(
                              shaderCallback: (bounds) => LinearGradient(
                                colors: isDark
                                    ? [
                                        const Color(0xFFF0F6FC),
                                        const Color(0xFFB8D4F0),
                                      ]
                                    : [
                                        const Color(0xFF0F172A),
                                        const Color(0xFF334155),
                                      ],
                              ).createShader(bounds),
                              child: const Text(
                                'NEPTUN',
                                style: TextStyle(
                                  fontSize: 38,
                                  fontWeight: FontWeight.w800,
                                  color: Colors.white,
                                  letterSpacing: 10,
                                ),
                              ),
                            ),
                          ),
                          const SizedBox(height: 10),

                          // Subtitle
                          Transform.translate(
                            offset: Offset(0, _slideAnimation.value * 0.6),
                            child: Text(
                              'Повітряні тривоги',
                              style: TextStyle(
                                fontSize: 14,
                                fontWeight: FontWeight.w500,
                                color: subtitleColor.withValues(alpha: 0.9),
                                letterSpacing: 3,
                              ),
                            ),
                          ),
                          const SizedBox(height: 52),

                          // Shimmer loading bar (isolated rebuild)
                          AnimatedBuilder(
                            animation: _shimmerController,
                            builder: (context, _) => SizedBox(
                              width: 140,
                              height: 3,
                              child: ClipRRect(
                                borderRadius: BorderRadius.circular(2),
                                child: Stack(
                                  children: [
                                    // Track
                                    Container(
                                      color: isDark
                                          ? Colors.white.withValues(alpha: 0.06)
                                          : Colors.black.withValues(
                                              alpha: 0.06,
                                            ),
                                    ),
                                    // Shimmer
                                    Positioned(
                                      left: _shimmerAnimation.value * 140 - 70,
                                      top: 0,
                                      bottom: 0,
                                      child: Container(
                                        width: 70,
                                        decoration: BoxDecoration(
                                          gradient: LinearGradient(
                                            colors: [
                                              Colors.transparent,
                                              accentColor.withValues(
                                                alpha: 0.8,
                                              ),
                                              Colors.transparent,
                                            ],
                                          ),
                                          borderRadius: BorderRadius.circular(
                                            2,
                                          ),
                                        ),
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}
