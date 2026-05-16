import 'dart:io';
import 'package:flutter/widgets.dart';
import 'package:google_mobile_ads/google_mobile_ads.dart';
import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:app_tracking_transparency/app_tracking_transparency.dart';

class AdService with WidgetsBindingObserver {
  static final AdService _instance = AdService._internal();
  factory AdService() => _instance;
  AdService._internal();

  BannerAd? _bannerAd;
  AppOpenAd? _appOpenAd;
  bool _isBannerAdLoaded = false;
  bool _isAppOpenAdLoaded = false;
  bool _isInitialized = false;
  bool _isPremium = false;
  int _bannerRetryCount = 0;
  DateTime? _lastAdRequestTime;
  int _totalAdRequestsThisSession = 0;
  static const int _maxRequestsPerSession = 5;
  TrackingStatus? _trackingStatus;

  // === APP OPEN AD SAFETY FLAGS ===
  // Prevents cold-start impressions which trigger AdMob "invalid traffic"
  bool _hasCompletedFirstSession = false;
  bool _hasShownColdStartAppOpen = false;
  DateTime? _backgroundedAt;
  static const Duration _minBackgroundDuration = Duration(seconds: 15);
  static const String _lastAppOpenShowKey = 'last_app_open_ad_shown';
  static const Duration _appOpenCooldown = Duration(hours: 1, minutes: 30);

  TrackingStatus? get trackingStatus => _trackingStatus;

  /// Called from main() after ATT is requested — allows AdService to use the result
  /// without requesting again (avoids duplicate prompts).
  void setATTStatus(TrackingStatus status) {
    _trackingStatus = status;
  }

  // Бонус після перегляду реклами - сховати банер на час
  static const String _adFreeUntilKey = 'ad_free_until';
  DateTime? _adFreeUntil;
  bool get isAdFree =>
      _adFreeUntil != null && DateTime.now().isBefore(_adFreeUntil!);

  // App Open Ad Unit ID
  static String get appOpenAdUnitId {
    if (Platform.isAndroid) {
      if (kDebugMode) {
        return 'ca-app-pub-3940256099942544/9257395921';
      }
      return 'ca-app-pub-1995509849440582/5738204880';
    } else if (Platform.isIOS) {
      if (kDebugMode) {
        return 'ca-app-pub-3940256099942544/5575463023';
      }
      return 'ca-app-pub-1995509849440582/1062877523';
    }
    return '';
  }

  // Ad Unit IDs
  static String get bannerAdUnitId {
    if (Platform.isAndroid) {
      if (kDebugMode) {
        return 'ca-app-pub-3940256099942544/6300978111';
      }
      return 'ca-app-pub-1995509849440582/1226737518';
    } else if (Platform.isIOS) {
      if (kDebugMode) {
        return 'ca-app-pub-3940256099942544/2934735716';
      }
      return 'ca-app-pub-1995509849440582/5593859915';
    }
    return '';
  }

  bool get isBannerAdLoaded => _isBannerAdLoaded && !isAdFree && !_isPremium;
  bool get isAppOpenAdLoaded => _isAppOpenAdLoaded && !_isPremium;
  BannerAd? get bannerAd => (isAdFree || _isPremium) ? null : _bannerAd;

  bool get debugIsPremium => _isPremium;
  bool get debugIsBannerLoaded => _isBannerAdLoaded;
  bool get debugIsAdFree => isAdFree;
  bool get debugIsInitialized => _isInitialized;
  String get debugLastError => _lastError;

  String _lastError = '';

  Future<void> initialize() async {
    if (_isInitialized) {
      debugPrint('AdMob already initialized, skipping');
      return;
    }

    try {
      final prefs = await SharedPreferences.getInstance();
      _isPremium = prefs.getBool('is_premium') ?? false;

      // Restore ad-free bonus from previous session
      final adFreeMillis = prefs.getInt(_adFreeUntilKey);
      if (adFreeMillis != null) {
        final stored = DateTime.fromMillisecondsSinceEpoch(adFreeMillis);
        if (DateTime.now().isBefore(stored)) {
          _adFreeUntil = stored;
          debugPrint('Restored ad-free bonus until $_adFreeUntil');
        } else {
          await prefs.remove(_adFreeUntilKey);
        }
      }

      if (_isPremium) {
        debugPrint('User has Premium - not initializing ads');
        return;
      }
    } catch (e) {
      debugPrint('Error checking premium: $e');
    }

    try {
      if (Platform.isIOS) {
        // ATT was already requested in main() before any ad code.
        // Just read status if not yet set (e.g. if AdService init ran before main's ATT).
        await _syncTrackingStatus();
      }

      await MobileAds.instance.initialize();

      await MobileAds.instance.updateRequestConfiguration(
        RequestConfiguration(
          testDeviceIds: kDebugMode ? ['B76A128AB5C15A27C13B13D68AFD2CC0'] : null,
          maxAdContentRating: MaxAdContentRating.g,
          tagForChildDirectedTreatment:
              TagForChildDirectedTreatment.unspecified,
          tagForUnderAgeOfConsent: TagForUnderAgeOfConsent.unspecified,
        ),
      );

      _isInitialized = true;
      debugPrint('AdMob initialized with content filtering');

      // Register lifecycle observer for App Open Ad on resume
      WidgetsBinding.instance.addObserver(this);

      if (!_isPremium) {
        // Pre-load all ads immediately — users often close app in 5s, delay = lost impressions
        debugPrint('🚀 Loading App Open Ad silently...');
        _loadAppOpenAdSilently();
        loadBannerAd();

        // App Open on cold start: 5s (was 12s) — users close fast, show while they're still there
        final coldStartDelay = kDebugMode ? 4 : 5;
        debugPrint(
          '🚀 Will attempt cold start App Open in $coldStartDelay seconds',
        );
        Future.delayed(Duration(seconds: coldStartDelay), () async {
          debugPrint('🚀 Cold start timer fired, premium=$_isPremium');
          if (!_isPremium) {
            await _tryShowAppOpenOnColdStart();
          }
        });
      }
    } catch (e) {
      debugPrint('AdMob initialization error: $e');
    }
  }

  void setPremiumStatus(bool isPremium) {
    _isPremium = isPremium;
    if (isPremium) {
      disposeBannerAd();
      _appOpenAd?.dispose();
      _appOpenAd = null;
      _isAppOpenAdLoaded = false;
      debugPrint('Premium activated - all ads disposed');
    }
  }

  // === LIFECYCLE OBSERVER FOR SAFE APP OPEN ADS ===
  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (state == AppLifecycleState.paused) {
      _backgroundedAt = DateTime.now();
    } else if (state == AppLifecycleState.resumed) {
      _onAppResumed();
    }
  }

  /// Called when app returns to foreground.
  /// Only shows App Open Ad if all safety conditions are met.
  Future<void> _onAppResumed() async {
    debugPrint('🚀 App resumed - checking App Open Ad conditions...');

    // In debug mode, skip most safety checks for easier testing
    if (kDebugMode) {
      debugPrint('🧪 Debug mode - relaxed App Open Ad checks');
      if (_isPremium || isAdFree) {
        debugPrint('🚀 Skipping - premium=$_isPremium, adFree=$isAdFree');
        return;
      }
      // Still need minimum 3 seconds in background in debug
      if (_backgroundedAt != null) {
        final bgDuration = DateTime.now().difference(_backgroundedAt!);
        if (bgDuration.inSeconds >= 3) {
          debugPrint(
            '🚀 Debug: showing App Open Ad (bg ${bgDuration.inSeconds}s)',
          );
          _showAppOpenAdInternal();
          return;
        } else {
          debugPrint('🚀 Debug: bg only ${bgDuration.inSeconds}s, need 3s');
        }
      }
      return;
    }

    // CONDITION 1: Must have completed at least one session
    if (!_hasCompletedFirstSession) {
      debugPrint('🚀 Skipping - first session not completed');
      if (!_isBannerAdLoaded) loadBannerAd();
      return;
    }

    // CONDITION 2: Must have been backgrounded for at least 15 seconds
    if (_backgroundedAt == null) {
      debugPrint('🚀 Skipping - no background timestamp');
      if (!_isBannerAdLoaded) loadBannerAd();
      return;
    }
    final backgroundDuration = DateTime.now().difference(_backgroundedAt!);
    if (backgroundDuration < _minBackgroundDuration) {
      debugPrint(
        '🚀 Skipping - bg only ${backgroundDuration.inSeconds}s, need ${_minBackgroundDuration.inSeconds}s',
      );
      return;
    }

    // CONDITION 3: Check persistent cooldown
    if (!await _canShowAppOpenAd()) {
      debugPrint('🚀 Skipping - cooldown not elapsed');
      _loadAppOpenAdSilently();
      if (!_isBannerAdLoaded) loadBannerAd();
      return;
    }

    // CONDITION 4: Not premium and not in ad-free period
    if (_isPremium || isAdFree) {
      debugPrint('🚀 Skipping - premium=$_isPremium, adFree=$isAdFree');
      if (!_isBannerAdLoaded) loadBannerAd();
      return;
    }

    debugPrint('🚀 All conditions met - showing App Open Ad');
    _showAppOpenAdInternal();
  }

  /// Mark that user has completed meaningful engagement.
  /// Call this after user has viewed main content.
  void markSessionActive() {
    _hasCompletedFirstSession = true;
  }

  /// Try showing App Open Ad on cold start (first app launch in session).
  Future<void> _tryShowAppOpenOnColdStart() async {
    debugPrint(
      '🚀 Cold start check: shown=$_hasShownColdStartAppOpen, session=$_hasCompletedFirstSession, premium=$_isPremium, adFree=$isAdFree, loaded=$_isAppOpenAdLoaded',
    );

    if (_hasShownColdStartAppOpen) {
      debugPrint('🚀 Cold start skip - already shown this session');
      return;
    }
    if (!_hasCompletedFirstSession) {
      debugPrint('🚀 Cold start skip - session not active');
      return;
    }
    if (_isPremium || isAdFree) {
      debugPrint('🚀 Cold start skip - premium=$_isPremium, adFree=$isAdFree');
      return;
    }

    // Skip cooldown in debug mode for testing
    if (!kDebugMode && !await _canShowAppOpenAd()) {
      debugPrint('🚀 Cold start skip - cooldown not elapsed');
      return;
    }
    if (kDebugMode) {
      debugPrint('🧪 Debug mode - skipping cooldown check');
    }

    if (!_isAppOpenAdLoaded || _appOpenAd == null) {
      debugPrint('🚀 Cold start - ad not loaded, loading now...');
      _loadAppOpenAdSilently();
      // One short retry to allow async load to complete
      await Future.delayed(const Duration(seconds: 3));
    }

    if (_appOpenAd != null && _isAppOpenAdLoaded) {
      debugPrint('🚀 Cold start: SHOWING App Open Ad NOW');
      _hasShownColdStartAppOpen = true;
      _showAppOpenAdInternal();
    } else {
      debugPrint('🚀 Cold start skip - App Open still not loaded after wait');
    }
  }

  Future<bool> _canShowAppOpenAd() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final lastShown = prefs.getInt(_lastAppOpenShowKey);
      if (lastShown == null) {
        return true;
      }
      final lastShownTime = DateTime.fromMillisecondsSinceEpoch(lastShown);
      return DateTime.now().difference(lastShownTime) >= _appOpenCooldown;
    } catch (e) {
      return true;
    }
  }

  Future<void> _recordAppOpenAdShown() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setInt(
        _lastAppOpenShowKey,
        DateTime.now().millisecondsSinceEpoch,
      );
    } catch (e) {
      debugPrint('Failed to record App Open Ad timestamp: $e');
    }
  }

  /// Load App Open Ad silently without auto-show.
  void _loadAppOpenAdSilently() {
    if (_isPremium || _isAppOpenAdLoaded) {
      return;
    }

    AppOpenAd.load(
      adUnitId: appOpenAdUnitId,
      request: const AdRequest(),
      adLoadCallback: AppOpenAdLoadCallback(
        onAdLoaded: (ad) {
          debugPrint('App Open ad loaded');
          _appOpenAd = ad;
          _isAppOpenAdLoaded = true;
          // Do NOT auto-show - wait for lifecycle trigger
        },
        onAdFailedToLoad: (error) {
          debugPrint('App Open ad failed to load: $error');
          _isAppOpenAdLoaded = false;
        },
      ),
    );
  }

  void _showAppOpenAdInternal() {
    if (_appOpenAd == null || !_isAppOpenAdLoaded) {
      _loadAppOpenAdSilently();
      return;
    }

    _appOpenAd!.fullScreenContentCallback = FullScreenContentCallback(
      onAdShowedFullScreenContent: (ad) {
        debugPrint('App Open ad showed');
        _recordAppOpenAdShown();
        _backgroundedAt = null; // Reset to prevent stale timestamp
      },
      onAdDismissedFullScreenContent: (ad) {
        debugPrint('App Open ad dismissed');
        _backgroundedAt = null; // Reset to prevent stale timestamp
        ad.dispose();
        _appOpenAd = null;
        _isAppOpenAdLoaded = false;
        _loadAppOpenAdSilently();
      },
      onAdFailedToShowFullScreenContent: (ad, error) {
        debugPrint('App Open ad failed to show: $error');
        _backgroundedAt = null; // Reset to prevent stale timestamp
        ad.dispose();
        _appOpenAd = null;
        _isAppOpenAdLoaded = false;
      },
    );

    _appOpenAd!.show();
  }

  void loadBannerAd({Function()? onLoaded}) async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final isPremiumFromPrefs = prefs.getBool('is_premium') ?? false;
      if (isPremiumFromPrefs) {
        _isPremium = true;
        debugPrint('User has Premium (from prefs) - skipping banner ad');
        return;
      }
    } catch (e) {
      debugPrint('Error checking premium in loadBannerAd: $e');
    }

    if (_isPremium) {
      debugPrint('User has Premium - skipping banner ad');
      return;
    }

    // Skip rate limiting in debug mode for easier testing
    if (!kDebugMode) {
      if (_totalAdRequestsThisSession >= _maxRequestsPerSession) {
        debugPrint(
          'AdMob session limit reached ($_maxRequestsPerSession requests) - skipping',
        );
        return;
      }

      final now = DateTime.now();
      if (_lastAdRequestTime != null &&
          now.difference(_lastAdRequestTime!).inSeconds < 120) {
        debugPrint('AdMob throttled - wait 120 seconds between requests');
        return;
      }
    } else {
      debugPrint('🧪 Debug mode - skipping ad rate limits');
    }

    if (!_isInitialized) {
      debugPrint('AdMob not initialized yet - will retry banner load');
      Future.delayed(const Duration(seconds: 2), () {
        if (_isInitialized && !_isPremium && !_isBannerAdLoaded) {
          loadBannerAd(onLoaded: onLoaded);
        }
      });
      return;
    }

    if (_isBannerAdLoaded && _bannerAd != null) {
      debugPrint('Banner ad already loaded');
      onLoaded?.call();
      return;
    }

    if (_bannerAd != null) {
      debugPrint('Disposing existing banner before reload');
      _bannerAd!.dispose();
      _bannerAd = null;
      _isBannerAdLoaded = false;
    }

    _lastAdRequestTime = DateTime.now();
    _totalAdRequestsThisSession++;

    // Get screen width for adaptive banner
    final screenWidth = MediaQueryData.fromView(
      WidgetsBinding.instance.platformDispatcher.views.first,
    ).size.width.truncate();

    // Use adaptive banner size, fallback to standard banner if width is invalid
    AdSize adSize = AdSize.banner;
    if (screenWidth > 0) {
      final adaptiveSize =
          await AdSize.getCurrentOrientationAnchoredAdaptiveBannerAdSize(
            screenWidth,
          );
      // CRITICAL: Only use adaptive size if height > 0, otherwise AdMob crashes
      if (adaptiveSize != null && adaptiveSize.height > 0) {
        adSize = adaptiveSize;
        debugPrint('Using adaptive banner: ${adSize.width}x${adSize.height}');
      } else {
        debugPrint(
          '⚠️ Adaptive size invalid (height=${adaptiveSize?.height}), using standard banner',
        );
      }
    } else {
      debugPrint(
        '⚠️ Screen width invalid ($screenWidth), using standard banner',
      );
    }
    debugPrint('Final banner ad size: ${adSize.width}x${adSize.height}');

    _bannerAd = BannerAd(
      adUnitId: bannerAdUnitId,
      size: adSize,
      request: const AdRequest(),
      listener: BannerAdListener(
        onAdLoaded: (ad) {
          if (_isPremium) {
            debugPrint('User became Premium - disposing banner');
            ad.dispose();
            _isBannerAdLoaded = false;
            return;
          }
          debugPrint('Banner ad loaded successfully');
          _isBannerAdLoaded = true;
          _bannerRetryCount = 0;
          _lastError = '';
          onLoaded?.call();
        },
        onAdFailedToLoad: (ad, error) {
          debugPrint('Banner ad failed to load: $error');
          _lastError = error.toString();
          ad.dispose();
          _bannerAd = null;
          _isBannerAdLoaded = false;
          _bannerRetryCount++;
          if (_bannerRetryCount <= 3 &&
              _totalAdRequestsThisSession < _maxRequestsPerSession) {
            debugPrint(
              'Banner retry #$_bannerRetryCount scheduled in 60s (max 3)',
            );
            Future.delayed(const Duration(seconds: 60), () {
              if (!_isPremium && !_isBannerAdLoaded) {
                debugPrint('Retrying banner ad load...');
                loadBannerAd(onLoaded: onLoaded);
              }
            });
          } else {
            debugPrint(
              'Banner retry limit reached. No more retries this session.',
            );
          }
        },
        onAdOpened: (ad) => debugPrint('Banner ad opened'),
        onAdClosed: (ad) => debugPrint('Banner ad closed'),
      ),
    );
    _bannerAd!.load();
  }

  void disposeBannerAd() {
    _bannerAd?.dispose();
    _bannerAd = null;
    _isBannerAdLoaded = false;
  }

  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    _bannerAd?.dispose();
    _appOpenAd?.dispose();
  }

  // ============== iOS App Tracking Transparency ==============
  // ATT is requested in main.dart _requestATTForIOS() BEFORE any ad code runs.
  // AdService only syncs the status here.

  Future<void> _syncTrackingStatus() async {
    try {
      if (_trackingStatus == null) {
        _trackingStatus =
            await AppTrackingTransparency.trackingAuthorizationStatus;
        debugPrint('AdService: ATT status = $_trackingStatus');
      }

      if (_trackingStatus == TrackingStatus.authorized) {
        final idfa = await AppTrackingTransparency.getAdvertisingIdentifier();
        debugPrint('IDFA available: ${idfa.isNotEmpty}');
      }
    } catch (e) {
      debugPrint('ATT sync error: $e');
    }
  }

  bool get isTrackingAuthorized => _trackingStatus == TrackingStatus.authorized;

  String get trackingStatusString {
    switch (_trackingStatus) {
      case TrackingStatus.authorized:
        return 'Дозволено';
      case TrackingStatus.denied:
        return 'Заборонено';
      case TrackingStatus.restricted:
        return 'Обмежено';
      case TrackingStatus.notDetermined:
        return 'Не визначено';
      case TrackingStatus.notSupported:
        return 'Не підтримується';
      case null:
        return 'Невідомо';
    }
  }
}
