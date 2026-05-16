import 'package:flutter/material.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/gestures.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:flutter/services.dart';
import 'package:firebase_core/firebase_core.dart';
import 'dart:math' as math;
import 'dart:ui' show ImageFilter;
import 'package:firebase_analytics/firebase_analytics.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'theme/app_theme.dart';
import 'theme/diary_design.dart';
import 'design/design_exports.dart';
import 'core/router/app_router.dart';
import 'services/notification_service.dart';
import 'services/chat_service.dart';
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
import 'features/chat/presentation/providers/chat_controller.dart';
import 'core/error/error_handler.dart';
import 'core/providers/providers.dart';
import 'services/map_data_service.dart';
import 'core/utils/app_debug_log.dart';
import 'config/app_constants.dart';
import 'pages/app_update_required_page.dart';
import 'services/app_version_gate_service.dart';

/// `flutter run --dart-define=NEPTUN_PERF_OVERLAY=true` (debug/profile) — FPS / frame timing bars.
const bool kNeptunPerfOverlay = bool.fromEnvironment(
  'NEPTUN_PERF_OVERLAY',
  defaultValue: false,
);

/// Плавніший скрол на планшетах / трекпаді; не змінює вигляд на телефоні.
final class NeptunScrollBehavior extends MaterialScrollBehavior {
  const NeptunScrollBehavior();

  @override
  Set<PointerDeviceKind> get dragDevices => {
    PointerDeviceKind.touch,
    PointerDeviceKind.stylus,
    PointerDeviceKind.mouse,
    PointerDeviceKind.trackpad,
  };
}

bool get _isIosNative => !kIsWeb && defaultTargetPlatform == TargetPlatform.iOS;

bool get _isAndroidNative =>
    !kIsWeb && defaultTargetPlatform == TargetPlatform.android;

// --- Initialization Logic ---

void main() async {
  // Global framework error handler to prevent Grey Screens of Death
  FlutterError.onError = (FlutterErrorDetails details) {
    // Suppress webview_flutter_wkwebview Pigeon null-assertion noise (iOS edge cases)
    final combined = '${details.exception}${details.stack}';
    if (combined.contains('web_kit.g.dart')) {
      appDebugLog(
        '⚠️ webview_flutter_wkwebview Pigeon assertion (known issue, ignored)',
      );
      return;
    }
    appDebugLog('🛑 FLUTTER FRAMEWORK ERROR: ${details.exception}');
    if (kDebugMode) {
      debugPrintStack(stackTrace: details.stack);
    }
    // Non-critical errors are swallowed to preserve UI state where possible.
  };

  runZonedGuarded(
    () async {
      WidgetsFlutterBinding.ensureInitialized();
      // Plus Jakarta Sans: bundled under assets/google_fonts/*.ttf (see pubspec).
      // Keep runtime fetching on so other families (e.g. Inter on feedback) still load.
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

      final appRouter = AppRouter(prefs: sl<SharedPreferences>());
      final router = appRouter.router;
      sl.registerSingleton<GoRouter>(router);

      runApp(ProviderScope(child: NeptunAlarmApp(router: appRouter.router)));

      // Defer platform-specific SDK/FCM logging so first frame renders immediately
      _deferredInit();
      _initializeServicesInBackground();
    },
    (error, stackTrace) {
      appDebugLog('🛑 DART ASYNC ERROR CAUGHT: $error');
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

    appDebugLog('✅ iOS initialization complete');
  } catch (e) {
    appDebugLog('❌ iOS initialization error: $e');
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
      appDebugLog(
        '⚠️ Battery optimization is enabled - notifications may be delayed',
      );
    }
  }

  appDebugLog('✅ Android initialization complete');
}

Future<void> _initFirebase() async {
  // Web requires a registered Web app + FirebaseOptions (flutterfire configure).
  // Calling initializeApp() here without options leaves the JS SDK in a bad state
  // (FirebaseError: No Firebase App '[DEFAULT]' in microtasks).
  if (kIsWeb) {
    appDebugLog(
      'Firebase: skipped on web (add Web app in Firebase Console + firebase_options.dart to enable)',
    );
    return;
  }
  try {
    await Firebase.initializeApp();
    final analytics = FirebaseAnalytics.instance;
    await analytics.setAnalyticsCollectionEnabled(true);
    appDebugLog('Firebase & Analytics initialized successfully');
  } catch (e) {
    appDebugLog('Firebase initialization failed: $e');
  }
}

Future<void> _initAdMobSdk() async {
  appDebugLog('AdMob SDK will be initialized by AdService');
}

/// Run after first frame — avoids blocking splash
Future<void> _deferredInit() async {
  // Android: init Firebase before FCM debug. (Web skips Firebase in _initFirebase.)
  if (_isAndroidNative) {
    await _initFirebase();
  }

  // Mobile platform initializations (background)
  if (_isIosNative) {
    unawaited(_initializeiOS());
    // ATT викликається в [_initializeServicesInBackground] перед AdMob — не дублювати тут.
  } else if (_isAndroidNative) {
    unawaited(_initializeAndroid());
  }

  if (!kIsWeb) {
    FirebaseMessaging.onBackgroundMessage(firebaseMessagingBackgroundHandler);
    appDebugLog('✅ onBackgroundMessage registered');
  }

  await ErrorHandler.initialize(
    dsn: const String.fromEnvironment('SENTRY_DSN', defaultValue: ''),
  );

  // Sentry replaces FlutterError.onError — wrap its handler with our filter
  final sentryHandler = FlutterError.onError;
  FlutterError.onError = (FlutterErrorDetails details) {
    final combined = '${details.exception}${details.stack}';
    if (combined.contains('web_kit.g.dart')) {
      appDebugLog('⚠️ webview Pigeon assertion (ignored)');
      return;
    }
    sentryHandler?.call(details);
  };

  await _logFcmDebugInfo();
}

/// Log FCM and APNS tokens for debugging push notification issues
Future<void> _logFcmDebugInfo() async {
  try {
    if (kIsWeb) return;
    if (Firebase.apps.isEmpty) {
      appDebugLog('⚠️ Firebase not initialized — skipping FCM debug log');
      return;
    }
    final messaging = FirebaseMessaging.instance;

    // On iOS, APNS token must be available for FCM topics to work
    if (_isIosNative) {
      final apnsToken = await messaging.getAPNSToken();
      appDebugLog(
        '🍎 APNS token: ${apnsToken != null ? "${apnsToken.substring(0, math.min(20, apnsToken.length))}..." : "NULL ⚠️ (topics will not work!)"}',
      );
      // Don't call getToken() if APNS isn't ready — it throws on iOS
      if (apnsToken == null) {
        return;
      }
    }

    final fcmToken = await messaging.getToken();
    appDebugLog(
      '🔑 FCM token: ${fcmToken != null ? "${fcmToken.substring(0, math.min(20, fcmToken.length))}..." : "NULL ⚠️"}',
    );
  } catch (e) {
    appDebugLog('⚠️ FCM debug info error: $e');
  }
}

Future<void> _initializeServicesInBackground() async {
  // Initialize PurchaseService and NotificationService in parallel
  // (don't block notifications waiting for purchases)
  if (_isAndroidNative) {
    await Future.wait([_initPurchaseService(), _initNotificationService()]);
    // Реклама після IAP, але не блокуємо cold start: UMP/GMA можуть підвисати на симуляторі.
    _scheduleAdServiceInit();
    _initWidgetService();
    _initReviewService();
  } else if (_isIosNative) {
    await _initPurchaseService();
    _scheduleAdServiceInit();
    await _initNotificationService();
    _initWidgetService();
    _initReviewService();
  }

  _initTtsService();

  // Chat service init (device ID, nickname)
  await sl<ChatService>().init();

  // Prefetch map data to warm caches (deferred, non-blocking)
  unawaited(
    Future.delayed(const Duration(seconds: 3), () async {
      try {
        await sl<MapDataService>().fetchAlarms();
      } catch (_) {}
    }),
  );
}

Future<void> _initPurchaseService() async {
  try {
    await PurchaseService().initialize();
    // Debug premium disabled — test non-premium flow on emulator
    appDebugLog('PurchaseService initialized');
  } catch (e) {
    appDebugLog('PurchaseService failed: $e');
  }
}

/// UMP + Mobile Ads не тримають ланцюжок запуску: сплеш, роутер і чат піднімаються раніше.
void _scheduleAdServiceInit() {
  unawaited(_initAdServiceDeferred());
}

Future<void> _initAdServiceDeferred() async {
  try {
    await Future<void>.delayed(const Duration(milliseconds: 900));
    final prefs = await SharedPreferences.getInstance();
    if (prefs.getBool('is_premium') ?? false) {
      appDebugLog('AdMob skipped — user is PRO (prefs)');
      return;
    }
    await AdService().initialize();
    appDebugLog('AdMob initialized');
  } catch (e) {
    appDebugLog('AdMob failed: $e');
  }
}

Future<void> _initNotificationService() async {
  try {
    await NotificationService().initialize();
    appDebugLog('NotificationService initialized');
    AlarmTrackingService().startTracking();
    appDebugLog('AlarmTrackingService started');
  } catch (e) {
    appDebugLog('NotificationService failed: $e');
  }
}

Future<void> _initTtsService() async {
  try {
    await TtsService().initialize();
    appDebugLog('TtsService initialized');
  } catch (e) {
    appDebugLog('TtsService failed: $e');
  }
}

Future<void> _initReviewService() async {
  try {
    await ReviewService().trackAppOpen();
    appDebugLog('ReviewService tracked app open');
  } catch (e) {
    appDebugLog('ReviewService failed: $e');
  }
}

Future<void> _initWidgetService() async {
  try {
    await WidgetService().initialize();
    appDebugLog('WidgetService initialized');
  } catch (e) {
    appDebugLog('WidgetService failed: $e');
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
  DateTime? _lastBackgroundedAt;
  bool _versionCheckDone = false;
  bool _versionBlocked = false;
  AppVersionBlockPayload? _versionBlockPayload;
  /// Після зміни теми — не дёргати [SystemChrome] одразу (ріже з [AnimatedTheme]).
  Timer? _systemUiSyncTimer;

  static const _minSplashDuration = Duration(milliseconds: 1500);
  static const _maxSplashDuration = Duration(seconds: 5);
  static const _fadeOutDuration = Duration(milliseconds: 520);

  @override
  void initState() {
    super.initState();
    _versionCheckDone = !(_isIosNative || _isAndroidNative);
    WidgetsBinding.instance.addObserver(this);

    // Apply system UI once after first frame (avoid platform channel every build).
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      final mode = ref.read(themeModeProvider);
      _updateSystemUI(mode == ThemeMode.dark);
    });

    ref.listenManual<ThemeMode>(themeModeProvider, (previous, next) {
      if (previous != next) {
        _systemUiSyncTimer?.cancel();
        _systemUiSyncTimer = Timer(AppConstants.themeSwitchDuration, () {
          _systemUiSyncTimer = null;
          if (!mounted) return;
          _updateSystemUI(ref.read(themeModeProvider) == ThemeMode.dark);
        });
      }
    });

    if (kDebugMode && kNeptunPerfOverlay) {
      appDebugLog(
        'NEPTUN_PERF_OVERLAY: use profile mode + Flutter DevTools → Performance',
      );
    }

    // Після першого кадру — щоб cold start / плагіни не зірвали таймер сплешу.
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      if (_isIosNative || _isAndroidNative) {
        unawaited(_runNativeVersionGate());
      }
      // Minimum display time so splash animation plays fully
      Future.delayed(_minSplashDuration, () {
        if (mounted) {
          setState(() => _minTimeElapsed = true);
          _tryDismissSplash();
        }
      });

      // Safety: never stay on splash forever (map/WebView / IAP can stall).
      // На нативі не знімаємо сплеш, доки не завершиться перевірка версії — див. [_tryDismissSplash].
      Future.delayed(_maxSplashDuration, () {
        if (mounted && _showSplash) {
          appDebugLog('⏱️ Splash max timeout reached — forcing dismiss');
          setState(() => _minTimeElapsed = true);
          _tryDismissSplash();
        }
      });
    });
  }

  /// Splash ends after [ _minSplashDuration ] — map tab has its own loader.
  /// (Previously we waited for [MapReadyNotifier]; that could stall if WebView never
  /// reported progress, and go_router [fullPath] is a route pattern, not URI path.)
  void _tryDismissSplash() {
    final waitingForVersion =
        (_isIosNative || _isAndroidNative) && !_versionCheckDone;
    if (waitingForVersion) return;
    if (_minTimeElapsed && _showSplash && mounted) {
      appDebugLog('✅ Splash dismissed — min time elapsed');
      _startFadeOut();
    }
  }

  Future<void> _runNativeVersionGate() async {
    try {
      final result = await AppVersionGateService.instance.evaluate();
      if (!mounted) return;
      setState(() {
        _versionCheckDone = true;
        if (result.isBlocked && result.block != null) {
          _versionBlocked = true;
          _versionBlockPayload = result.block;
          _showSplash = false;
        }
      });
      if (!mounted || _versionBlocked) return;
      _tryDismissSplash();
    } catch (e) {
      appDebugLog('app-version-gate: unexpected $e');
      if (!mounted) return;
      setState(() => _versionCheckDone = true);
      _tryDismissSplash();
    }
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
    } else if (state == AppLifecycleState.resumed) {
      final wasBg = _lastBackgroundedAt;
      if (wasBg != null) {
        final bgDuration = DateTime.now().difference(wasBg);
        if (bgDuration >= const Duration(seconds: 5)) {
          DataStreamService.instance.forceReconnectIfNeeded();
          NotificationService().reRegisterOnResume();
        }
      }
      _lastBackgroundedAt = null;
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (!mounted) return;
        unawaited(
          ref
              .read(chatControllerProvider.notifier)
              .syncMissedMessagesAfterReconnect(),
        );
      });
    }
  }

  @override
  void dispose() {
    _systemUiSyncTimer?.cancel();
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }

  void _updateSystemUI(bool isDark) {
    SystemChrome.setSystemUIOverlayStyle(
      SystemUiOverlayStyle(
        statusBarColor: Colors.transparent,
        statusBarIconBrightness: isDark ? Brightness.light : Brightness.dark,
        systemNavigationBarColor: isDark
            ? DiaryColors.darkBackground
            : DiaryColors.background,
        systemNavigationBarIconBrightness: isDark
            ? Brightness.light
            : Brightness.dark,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final themeMode = ref.watch(themeModeProvider);

    if (_versionBlocked && _versionBlockPayload != null) {
      return MaterialApp(
        title: AppConstants.appName,
        debugShowCheckedModeBanner: false,
        showPerformanceOverlay: kDebugMode && kNeptunPerfOverlay,
        scrollBehavior: const NeptunScrollBehavior(),
        themeMode: themeMode,
        theme: AppTheme.light,
        darkTheme: AppTheme.dark,
        themeAnimationDuration: AppConstants.themeSwitchDuration,
        themeAnimationCurve: AppConstants.themeSwitchCurve,
        themeAnimationStyle: AnimationStyle(
          duration: AppConstants.themeSwitchDuration,
          curve: AppConstants.themeSwitchCurve,
        ),
        home: AppUpdateRequiredPage(payload: _versionBlockPayload!),
      );
    }

    return MaterialApp.router(
      title: AppConstants.appName,
      debugShowCheckedModeBanner: false,
      showPerformanceOverlay: kDebugMode && kNeptunPerfOverlay,
      scrollBehavior: const NeptunScrollBehavior(),
      themeMode: themeMode,
      theme: AppTheme.light,
      darkTheme: AppTheme.dark,
      themeAnimationDuration: AppConstants.themeSwitchDuration,
      themeAnimationCurve: AppConstants.themeSwitchCurve,
      themeAnimationStyle: AnimationStyle(
        duration: AppConstants.themeSwitchDuration,
        curve: AppConstants.themeSwitchCurve,
      ),
      routerConfig: widget.router,
      builder: (context, child) {
        final media = MediaQuery.of(context);
        return MediaQuery(
          data: media.copyWith(
            textScaler: media.textScaler.clamp(
              minScaleFactor: 0.88,
              maxScaleFactor: 1.24,
            ),
          ),
          child: Stack(
            fit: StackFit.expand,
            children: [
              child ?? const SizedBox.shrink(),
              if (_showSplash)
                IgnorePointer(
                  ignoring: _splashOpacity < 1.0,
                  child: AnimatedOpacity(
                    opacity: _splashOpacity,
                    duration: _fadeOutDuration,
                    curve: Curves.easeOutCubic,
                    child: const _SplashScreen(),
                  ),
                ),
            ],
          ),
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
  late AnimationController _entrance;
  late AnimationController _ambient;
  late Animation<double> _scaleAnimation;
  late Animation<double> _opacityAnimation;
  late Animation<double> _slideAnimation;
  late Animation<double> _barAnimation;

  @override
  void initState() {
    super.initState();
    _entrance = AnimationController(
      duration: const Duration(milliseconds: 1100),
      vsync: this,
    )..forward();

    _ambient = AnimationController(
      duration: const Duration(milliseconds: 3200),
      vsync: this,
    )..repeat(reverse: true);

    _scaleAnimation = Tween<double>(begin: 0.82, end: 1.0).animate(
      CurvedAnimation(
        parent: _entrance,
        curve: Curves.easeOutBack,
      ),
    );
    _opacityAnimation = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(
        parent: _entrance,
        curve: const Interval(0.0, 0.45, curve: Curves.easeOut),
      ),
    );
    _slideAnimation = Tween<double>(begin: 28.0, end: 0.0).animate(
      CurvedAnimation(
        parent: _entrance,
        curve: const Interval(0.1, 0.82, curve: Curves.easeOutCubic),
      ),
    );
    _barAnimation = Tween<double>(begin: 0.06, end: 1.0).animate(
      CurvedAnimation(
        parent: _entrance,
        curve: const Interval(0.2, 0.92, curve: Curves.easeOutCubic),
      ),
    );
  }

  @override
  void dispose() {
    _entrance.dispose();
    _ambient.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final bg = isDark ? DiaryColors.darkBackground : DiaryColors.background;
    final fg = isDark ? DiaryColors.darkPrimary : DiaryColors.primary;
    final muted = isDark ? DiaryColors.darkMuted : DiaryColors.muted;
    final accent = isDark
        ? DiaryColors.darkPrimary.withValues(alpha: 0.12)
        : DiaryColors.primary.withValues(alpha: 0.08);
    // Ледь помітні «орби»: низька альфа + blur + radial fade (без різкого диска).
    final orbCore = isDark
        ? DiaryColors.darkPrimary.withValues(alpha: 0.045)
        : DiaryColors.primary.withValues(alpha: 0.034);
    const orbBlurSigma = 56.0;

    return Scaffold(
      backgroundColor: bg,
      body: RepaintBoundary(
        child: Stack(
          fit: StackFit.expand,
          children: [
            DecoratedBox(
              decoration: BoxDecoration(
                gradient: RadialGradient(
                  center: const Alignment(0, -0.32),
                  radius: 1.22,
                  colors: [accent, bg],
                  stops: const [0.0, 1.0],
                ),
              ),
            ),
            AnimatedBuilder(
              animation: Listenable.merge([_entrance, _ambient]),
              builder: (context, _) {
                final breathe = 0.5 + 0.5 * _ambient.value;
                final drift = (breathe - 0.5) * 18;
                final pulseScale = 1.0 + 0.035 * math.sin(_ambient.value * math.pi);
                return Stack(
                  fit: StackFit.expand,
                  children: [
                    Positioned(
                      right: -80 + drift,
                      top: 56 - drift * 0.4,
                      child: IgnorePointer(
                        child: ImageFiltered(
                          imageFilter: ImageFilter.blur(
                            sigmaX: orbBlurSigma,
                            sigmaY: orbBlurSigma,
                          ),
                          child: Container(
                            width: 280,
                            height: 280,
                            decoration: BoxDecoration(
                              shape: BoxShape.circle,
                              gradient: RadialGradient(
                                colors: [
                                  orbCore,
                                  orbCore.withValues(alpha: 0),
                                ],
                                stops: const [0.15, 1.0],
                              ),
                            ),
                          ),
                        ),
                      ),
                    ),
                    Positioned(
                      left: -56 - drift * 0.5,
                      bottom: 96 + drift * 0.3,
                      child: IgnorePointer(
                        child: ImageFiltered(
                          imageFilter: ImageFilter.blur(
                            sigmaX: orbBlurSigma * 0.92,
                            sigmaY: orbBlurSigma * 0.92,
                          ),
                          child: Container(
                            width: 260,
                            height: 260,
                            decoration: BoxDecoration(
                              shape: BoxShape.circle,
                              gradient: RadialGradient(
                                colors: [
                                  orbCore.withValues(alpha: 0.72),
                                  orbCore.withValues(alpha: 0),
                                ],
                                stops: const [0.12, 1.0],
                              ),
                            ),
                          ),
                        ),
                      ),
                    ),
                    Center(
                      child: Opacity(
                        opacity: _opacityAnimation.value,
                        child: Transform.scale(
                          scale: _scaleAnimation.value * pulseScale,
                          child: Column(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Container(
                                width: 118,
                                height: 118,
                                decoration: BoxDecoration(
                                  borderRadius: BorderRadius.circular(34),
                                  gradient: LinearGradient(
                                    begin: Alignment.topLeft,
                                    end: Alignment.bottomRight,
                                    colors: [
                                      fg,
                                      fg.withValues(alpha: isDark ? 0.88 : 0.92),
                                    ],
                                  ),
                                  boxShadow: [
                                    BoxShadow(
                                      color: fg.withValues(
                                        alpha: isDark ? 0.42 : 0.28,
                                      ),
                                      blurRadius: 32 + 8 * breathe,
                                      spreadRadius: -4,
                                      offset: Offset(0, 14 + 4 * breathe),
                                    ),
                                  ],
                                ),
                                child: Stack(
                                  alignment: Alignment.center,
                                  children: [
                                    Positioned.fill(
                                      child: DecoratedBox(
                                        decoration: BoxDecoration(
                                          borderRadius:
                                              BorderRadius.circular(34),
                                          border: Border.all(
                                            color: Colors.white.withValues(
                                              alpha: isDark ? 0.14 : 0.22,
                                            ),
                                            width: 1.2,
                                          ),
                                        ),
                                      ),
                                    ),
                                    Icon(
                                      Icons.shield_rounded,
                                      size: 54,
                                      color: isDark
                                          ? DiaryColors.darkOnPrimary
                                          : DiaryColors.onPrimary,
                                    ),
                                  ],
                                ),
                              ),
                              const SizedBox(height: 38),
                              Transform.translate(
                                offset: Offset(0, _slideAnimation.value),
                                child: Text(
                                  AppConstants.appName.toUpperCase(),
                                  style: NeptunTypography.h1Style.copyWith(
                                    fontSize: 23,
                                    fontWeight: FontWeight.w700,
                                    letterSpacing: 1.8,
                                    color: fg,
                                  ),
                                ),
                              ),
                              const SizedBox(height: 10),
                              Transform.translate(
                                offset: Offset(0, _slideAnimation.value * 0.72),
                                child: Text(
                                  'AIR MONITORING SYSTEM',
                                  style: NeptunTypography.microStyle.copyWith(
                                    fontWeight: FontWeight.w600,
                                    letterSpacing: 2.4,
                                    color: muted,
                                  ),
                                ),
                              ),
                              const SizedBox(height: 44),
                              SizedBox(
                                width: 140,
                                height: 4,
                                child: ClipRRect(
                                  borderRadius: BorderRadius.circular(999),
                                  child: Stack(
                                    fit: StackFit.expand,
                                    children: [
                                      ColoredBox(
                                        color: fg.withValues(alpha: 0.12),
                                      ),
                                      Align(
                                        alignment: Alignment.centerLeft,
                                        child: FractionallySizedBox(
                                          widthFactor: _barAnimation.value
                                              .clamp(0.02, 1.0),
                                          heightFactor: 1,
                                          alignment: Alignment.centerLeft,
                                          child: DecoratedBox(
                                            decoration: BoxDecoration(
                                              gradient: LinearGradient(
                                                colors: [
                                                  fg.withValues(alpha: 0.75),
                                                  fg,
                                                ],
                                              ),
                                            ),
                                          ),
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
                  ],
                );
              },
            ),
          ],
        ),
      ),
    );
  }
}
