import 'dart:async';
import 'dart:developer' as developer;
import 'dart:io';

import 'package:flutter/widgets.dart';
import 'package:google_mobile_ads/google_mobile_ads.dart';
import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:app_tracking_transparency/app_tracking_transparency.dart';
import 'package:neptun_alarm_app/core/utils/app_debug_log.dart';

class AdService with WidgetsBindingObserver {
  static final AdService _instance = AdService._internal();
  factory AdService() => _instance;
  AdService._internal();

  /// Bumped when banner visibility/load state changes so shell UI rebuilds.
  final ValueNotifier<int> bannerRebuildTick = ValueNotifier(0);

  void _notifyBannerDisplayChanged() {
    bannerRebuildTick.value++;
  }

  BannerAd? _bannerAd;
  AppOpenAd? _appOpenAd;
  InterstitialAd? _interstitialAd;
  bool _interstitialLoadInFlight = false;
  RewardedAd? _rewardedAd;
  bool _rewardedLoadInFlight = false;
  int _interstitialShowsSession = 0;
  DateTime? _monetizationReadyAt;
  bool _interstitialShowInProgress = false;
  bool _appOpenLoadInFlight = false;
  Timer? _appOpenPreloadAfterCooldownTimer;
  bool _isBannerAdLoaded = false;
  bool _isAppOpenAdLoaded = false;
  bool _isInitialized = false;
  bool _isPremium = false;
  int _bannerRetryCount = 0;
  DateTime? _lastAdRequestTime;
  int _totalAdRequestsThisSession = 0;
  /// Банер: ліміт запитів за сесію (занадто високий без потреби ріже fill у AdMob).
  static const int _maxRequestsPerSession = 34;
  TrackingStatus? _trackingStatus;

  // === APP OPEN AD SAFETY FLAGS ===
  // Prevents cold-start impressions which trigger AdMob "invalid traffic"
  bool _hasCompletedFirstSession = false;
  bool _hasShownColdStartAppOpen = false;
  DateTime? _backgroundedAt;
  /// Мінімум у фоні перед App Open (занадто мало → ризик «invalid traffic» у звітах).
  static const Duration _minBackgroundDuration = Duration(seconds: 12);
  static const String _lastAppOpenShowKey = 'last_app_open_ad_shown';
  static const String _lastInterstitialShownKey = 'last_interstitial_shown_ms';
  /// Між показами App Open. Частіше ~30 хв дає більше показів, але не кожен повернення в додаток.
  static const Duration _appOpenCooldown = Duration(minutes: 45);
  static const int _maxInterstitialPerSession = 24;
  /// Агресивний мінімум між міжсторонковими (~20 с); нижче — дратівливо й більше скарг / policy.
  static const Duration _interstitialMinInterval = Duration(seconds: 20);
  /// Після готовності AdMob — лишаємо кілька секунд на стабілізацію, потім можна показувати.
  static const Duration _minForegroundBeforeInterstitial = Duration(seconds: 4);
  /// Не накладати міжсторонкову одразу після App Open (два full-screen підряд).
  static const Duration _minGapAfterAppOpenForInterstitial = Duration(seconds: 12);

  /// `flutter run` або `--dart-define=NEPTUN_ADS_DEBUG_INTERSTITIALS=true` — коротші паузи, щоб міжсторінкову рекламу було легше піймати при тестах.
  static const bool _interstitialRelaxed =
      kDebugMode ||
      bool.fromEnvironment(
        'NEPTUN_ADS_DEBUG_INTERSTITIALS',
        defaultValue: false,
      );

  void _logInterstitialDiag(String msg) {
    if (kDebugMode || _interstitialRelaxed) {
      developer.log(msg, name: 'ads');
    }
  }

  /// Діагностика в release: на Android зручно `adb logcat -s NeptunAds`; на iOS `developer.log`
  /// часто не видно в Console — тому дублюємо через [debugPrint] (шукайте `[NeptunAds]` у
  /// терміналі `flutter run` або в Console).
  void _logAdsRelease(String msg) {
    developer.log(msg, name: 'NeptunAds');
    debugPrint('[NeptunAds] $msg');
  }

  Timer? _interstitialRetryTimer;
  int _interstitialLoadRetryCount = 0;

  void _scheduleInterstitialReloadBackoff(String unitId) {
    if (_isPremium || isAdFree || !_isInitialized || kIsWeb) return;
    if (_interstitialAd != null) return;
    if (_interstitialLoadRetryCount >= 6) {
      _logAdsRelease(
        'Interstitial: giving up after 6 failed loads (check AdMob Interstitial unit & app-ads.txt). unit=$unitId',
      );
      return;
    }
    _interstitialRetryTimer?.cancel();
    _interstitialLoadRetryCount++;
    final sec = 10 * _interstitialLoadRetryCount;
    _interstitialRetryTimer = Timer(Duration(seconds: sec), () {
      _interstitialRetryTimer = null;
      if (_isPremium || isAdFree || _interstitialAd != null) return;
      _logAdsRelease(
        'Interstitial: auto-retry $_interstitialLoadRetryCount after ${sec}s (unit=$unitId)',
      );
      unawaited(_preloadInterstitialAd());
    });
  }

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
    if (!kIsWeb && Platform.isAndroid) {
      if (kDebugMode) {
        return 'ca-app-pub-3940256099942544/9257395921';
      }
      return 'ca-app-pub-1995509849440582/5738204880';
    } else if (!kIsWeb && Platform.isIOS) {
      if (kDebugMode) {
        return 'ca-app-pub-3940256099942544/5575463023';
      }
      return 'ca-app-pub-1995509849440582/1062877523';
    }
    return '';
  }

  // Ad Unit IDs
  static String get bannerAdUnitId {
    if (!kIsWeb && Platform.isAndroid) {
      if (kDebugMode) {
        return 'ca-app-pub-3940256099942544/6300978111';
      }
      return 'ca-app-pub-1995509849440582/1226737518';
    } else if (!kIsWeb && Platform.isIOS) {
      if (kDebugMode) {
        return 'ca-app-pub-3940256099942544/2934735716';
      }
      return 'ca-app-pub-1995509849440582/5593859915';
    }
    return '';
  }

  /// Міжсторонкова реклама.
  /// **Debug:** тестовий ID Google (завжди є fill). **Release:** ваш блок типу *Interstitial*
  /// у AdMob для цього застосунку; якщо блок не створений або інший формат — завантаження впаде
  /// (див. logcat `NeptunAds`). Перевизначення: `--dart-define=NEPTUN_INTERSTITIAL_AD_UNIT=...`.
  static String get interstitialAdUnitId {
    const fromEnv = String.fromEnvironment('NEPTUN_INTERSTITIAL_AD_UNIT');
    if (fromEnv.isNotEmpty) return fromEnv;
    if (!kIsWeb && Platform.isAndroid) {
      if (kDebugMode) {
        return 'ca-app-pub-3940256099942544/1033173712';
      }
      return 'ca-app-pub-1995509849440582/1718952562';
    } else if (!kIsWeb && Platform.isIOS) {
      if (kDebugMode) {
        return 'ca-app-pub-3940256099942544/4411468910';
      }
      return 'ca-app-pub-1995509849440582/8092789228';
    }
    return '';
  }

  /// Заохочена реклама (Rewarded). ID мають бути з **окремих** блоків формату Rewarded у AdMob —
  /// ті самі, що міжсторонкові (`1718952562` / `8092789228`), використовувати не можна.
  /// Реліз: за замовчуванням порожньо — додайте блоки в AdMob і вставте нижче або передайте
  /// `--dart-define=NEPTUN_REWARDED_AD_UNIT=ca-app-pub-1995509849440582/...`.
  static String get rewardedAdUnitId {
    const fromEnv = String.fromEnvironment('NEPTUN_REWARDED_AD_UNIT');
    if (fromEnv.isNotEmpty) return fromEnv;
    if (!kIsWeb && Platform.isAndroid) {
      if (kDebugMode) {
        return 'ca-app-pub-3940256099942544/5224354917';
      }
      return '';
    } else if (!kIsWeb && Platform.isIOS) {
      if (kDebugMode) {
        return 'ca-app-pub-3940256099942544/1712485313';
      }
      return '';
    }
    return '';
  }

  bool get isBannerAdLoaded => _isBannerAdLoaded && !isAdFree && !_isPremium;
  bool get isAppOpenAdLoaded =>
      _isAppOpenAdLoaded && !_isPremium && !isAdFree;
  BannerAd? get bannerAd => (isAdFree || _isPremium) ? null : _bannerAd;

  bool get debugIsPremium => _isPremium;
  bool get debugIsBannerLoaded => _isBannerAdLoaded;
  bool get debugIsAdFree => isAdFree;
  bool get debugIsInitialized => _isInitialized;
  String get debugLastError => _lastError;

  String _lastError = '';

  Future<void> initialize() async {
    if (kIsWeb) {
      appDebugLog('Ads not supported on Web, skipping AdMob init');
      _isInitialized = true; // Mark as "initialized" so callers don't hang
      return;
    }

    if (_isInitialized) {
      appDebugLog('AdMob already initialized, skipping');
      return;
    }

    try {
      final prefs = await SharedPreferences.getInstance();
      // Only upgrade from prefs — never clobber _isPremium that was already set
      // by setPremiumStatus() racing with this init (e.g. PurchaseService debug PRO).
      final premiumPrefs = prefs.getBool('is_premium') ?? false;
      if (premiumPrefs) _isPremium = true;

      // Restore ad-free bonus from previous session
      final adFreeMillis = prefs.getInt(_adFreeUntilKey);
      if (adFreeMillis != null) {
        final stored = DateTime.fromMillisecondsSinceEpoch(adFreeMillis);
        if (DateTime.now().isBefore(stored)) {
          _adFreeUntil = stored;
          appDebugLog('Restored ad-free bonus until $_adFreeUntil');
        } else {
          await prefs.remove(_adFreeUntilKey);
        }
      }

      if (_isPremium) {
        appDebugLog('User has Premium - not initializing ads');
        _logAdsRelease('Init skipped: premium (is_premium in prefs)');
        return;
      }
    } catch (e) {
      appDebugLog('Error checking premium: $e');
    }

    try {
      await _ensureIosAttBeforeMobileAds();
      await _gatherConsentForAds();

      try {
        await MobileAds.instance
            .initialize()
            .timeout(const Duration(seconds: 25));
      } on TimeoutException catch (_) {
        appDebugLog('MobileAds.initialize timed out after 25s — ads disabled this session');
        _logAdsRelease(
          'MobileAds.initialize timed out after 25s — ads disabled this session',
        );
        return;
      }

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
      _monetizationReadyAt = DateTime.now();
      appDebugLog('AdMob initialized with content filtering');
      _logAdsRelease(
        'AdMob initialized; interstitial unit=$interstitialAdUnitId',
      );

      // Register lifecycle observer for App Open Ad on resume
      WidgetsBinding.instance.addObserver(this);

      if (!_isPremium) {
        // App Open: only preload when cooldown allows a show — otherwise AdMob counts
        // requests without matching impressions (same after dismiss).
        appDebugLog('🚀 App Open: preload if eligible (cooldown-aware)...');
        unawaited(_loadAppOpenAdSilently());
        loadBannerAd();
        unawaited(_preloadInterstitialAd());
        unawaited(_preloadRewardedAd());

        // Cold start App Open: коротка затримка, поки користувач ще в додатку.
        final coldStartDelay = 4;
        appDebugLog(
          '🚀 Will attempt cold start App Open in $coldStartDelay seconds',
        );
        Future.delayed(Duration(seconds: coldStartDelay), () async {
          appDebugLog('🚀 Cold start timer fired, premium=$_isPremium');
          if (!_isPremium) {
            await _tryShowAppOpenOnColdStart();
          }
        });
      }
    } catch (e) {
      appDebugLog('AdMob initialization error: $e');
      _logAdsRelease('AdMob initialization error: $e');
    }
  }

  void setPremiumStatus(bool isPremium) {
    final wasPremium = _isPremium;
    _isPremium = isPremium;
    if (isPremium) {
      _appOpenPreloadAfterCooldownTimer?.cancel();
      _appOpenPreloadAfterCooldownTimer = null;
      disposeBannerAd();
      _disposeInterstitialAd();
      _disposeRewardedAd();
      _appOpenAd?.dispose();
      _appOpenAd = null;
      _isAppOpenAdLoaded = false;
      appDebugLog('Premium activated - all ads disposed');
    } else if (wasPremium && _isInitialized) {
      appDebugLog('Premium off — reloading banner');
      loadBannerAd();
      unawaited(_preloadInterstitialAd());
      unawaited(_preloadRewardedAd());
    }
    _notifyBannerDisplayChanged();
  }

  /// PRO у prefs може з’явитися раніше, ніж [setPremiumStatus] — не показуємо рекламу.
  Future<void> _ensurePremiumFromPrefs() async {
    if (_isPremium) return;
    try {
      final prefs = await SharedPreferences.getInstance();
      if (prefs.getBool('is_premium') ?? false) {
        setPremiumStatus(true);
      }
    } catch (e) {
      appDebugLog('_ensurePremiumFromPrefs: $e');
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
    appDebugLog('🚀 App resumed - checking App Open Ad conditions...');
    await _ensurePremiumFromPrefs();

    // In debug mode, skip most safety checks for easier testing
    if (kDebugMode) {
      appDebugLog('🧪 Debug mode - relaxed App Open Ad checks');
      if (_isPremium || isAdFree) {
        appDebugLog('🚀 Skipping - premium=$_isPremium, adFree=$isAdFree');
        return;
      }
      // Still need minimum 3 seconds in background in debug
      if (_backgroundedAt != null) {
        final bgDuration = DateTime.now().difference(_backgroundedAt!);
        if (bgDuration.inSeconds >= 3) {
          appDebugLog(
            '🚀 Debug: showing App Open Ad (bg ${bgDuration.inSeconds}s)',
          );
          await _showAppOpenAdInternal();
          return;
        } else {
          appDebugLog('🚀 Debug: bg only ${bgDuration.inSeconds}s, need 3s');
        }
      }
      return;
    }

    // CONDITION 1: Must have completed at least one session
    if (!_hasCompletedFirstSession) {
      appDebugLog('🚀 Skipping - first session not completed');
      if (!_isBannerAdLoaded) loadBannerAd();
      return;
    }

    // CONDITION 2: Must have been backgrounded for at least 15 seconds
    if (_backgroundedAt == null) {
      appDebugLog('🚀 Skipping - no background timestamp');
      if (!_isBannerAdLoaded) loadBannerAd();
      return;
    }
    final backgroundDuration = DateTime.now().difference(_backgroundedAt!);
    if (backgroundDuration < _minBackgroundDuration) {
      appDebugLog(
        '🚀 Skipping - bg only ${backgroundDuration.inSeconds}s, need ${_minBackgroundDuration.inSeconds}s',
      );
      return;
    }

    // CONDITION 3: Check persistent cooldown
    if (!await _canShowAppOpenAd()) {
      appDebugLog('🚀 Skipping - cooldown not elapsed (no App Open preload)');
      if (!_isBannerAdLoaded) loadBannerAd();
      return;
    }

    // CONDITION 4: Not premium and not in ad-free period
    if (_isPremium || isAdFree) {
      appDebugLog('🚀 Skipping - premium=$_isPremium, adFree=$isAdFree');
      if (!_isBannerAdLoaded) loadBannerAd();
      return;
    }

    appDebugLog('🚀 All conditions met - showing App Open Ad');
    await _showAppOpenAdInternal();
  }

  /// Mark that user has completed meaningful engagement.
  /// Call this after user has viewed main content.
  void markSessionActive() {
    _hasCompletedFirstSession = true;
  }

  /// Try showing App Open Ad on cold start (first app launch in session).
  Future<void> _tryShowAppOpenOnColdStart() async {
    appDebugLog(
      '🚀 Cold start check: shown=$_hasShownColdStartAppOpen, session=$_hasCompletedFirstSession, premium=$_isPremium, adFree=$isAdFree, loaded=$_isAppOpenAdLoaded',
    );
    await _ensurePremiumFromPrefs();

    if (_hasShownColdStartAppOpen) {
      appDebugLog('🚀 Cold start skip - already shown this session');
      return;
    }
    if (!_hasCompletedFirstSession) {
      appDebugLog('🚀 Cold start skip - session not active');
      return;
    }
    if (_isPremium || isAdFree) {
      appDebugLog('🚀 Cold start skip - premium=$_isPremium, adFree=$isAdFree');
      return;
    }

    // Skip cooldown in debug mode for testing
    if (!kDebugMode && !await _canShowAppOpenAd()) {
      appDebugLog('🚀 Cold start skip - cooldown not elapsed');
      return;
    }
    if (kDebugMode) {
      appDebugLog('🧪 Debug mode - skipping cooldown check');
    }

    if (!_isAppOpenAdLoaded || _appOpenAd == null) {
      appDebugLog('🚀 Cold start - ad not loaded, loading now...');
      await _loadAppOpenAdSilently(bypassCooldown: true);
      // One short retry to allow async load to complete
      await Future.delayed(const Duration(seconds: 3));
    }

    if (_appOpenAd != null && _isAppOpenAdLoaded) {
      appDebugLog('🚀 Cold start: SHOWING App Open Ad NOW');
      _hasShownColdStartAppOpen = true;
      await _showAppOpenAdInternal();
    } else {
      appDebugLog('🚀 Cold start skip - App Open still not loaded after wait');
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
      appDebugLog('Failed to record App Open Ad timestamp: $e');
    }
  }

  /// Load App Open without auto-show. By default skips load while inter-show
  /// cooldown is active so AdMob does not record requests for ads that cannot
  /// be shown yet.
  Future<void> _loadAppOpenAdSilently({bool bypassCooldown = false}) async {
    await _ensurePremiumFromPrefs();
    if (_isPremium || isAdFree || _isAppOpenAdLoaded || _appOpenLoadInFlight) {
      return;
    }

    if (!bypassCooldown && !kDebugMode) {
      if (!await _canShowAppOpenAd()) {
        appDebugLog('App Open: skip load (cooldown active)');
        return;
      }
    }

    _appOpenLoadInFlight = true;
    AppOpenAd.load(
      adUnitId: appOpenAdUnitId,
      request: const AdRequest(),
      adLoadCallback: AppOpenAdLoadCallback(
        onAdLoaded: (ad) {
          _appOpenLoadInFlight = false;
          appDebugLog('App Open ad loaded');
          _appOpenAd = ad;
          _isAppOpenAdLoaded = true;
          // Do NOT auto-show - wait for lifecycle trigger
        },
        onAdFailedToLoad: (error) {
          _appOpenLoadInFlight = false;
          appDebugLog('App Open ad failed to load: $error');
          _isAppOpenAdLoaded = false;
        },
      ),
    );
  }

  Future<void> _showAppOpenAdInternal() async {
    await _ensurePremiumFromPrefs();
    if (_isPremium || isAdFree) return;

    if (_appOpenAd == null || !_isAppOpenAdLoaded) {
      unawaited(_loadAppOpenAdSilently(bypassCooldown: true));
      return;
    }

    _appOpenAd!.fullScreenContentCallback = FullScreenContentCallback(
      onAdShowedFullScreenContent: (ad) {
        appDebugLog('App Open ad showed');
        _recordAppOpenAdShown();
        _backgroundedAt = null; // Reset to prevent stale timestamp
      },
      onAdDismissedFullScreenContent: (ad) {
        appDebugLog('App Open ad dismissed');
        _backgroundedAt = null; // Reset to prevent stale timestamp
        ad.dispose();
        _appOpenAd = null;
        _isAppOpenAdLoaded = false;
        _scheduleAppOpenPreloadAfterCooldown();
      },
      onAdFailedToShowFullScreenContent: (ad, error) {
        appDebugLog('App Open ad failed to show: $error');
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
        appDebugLog('User has Premium (from prefs) - skipping banner ad');
        return;
      }
    } catch (e) {
      appDebugLog('Error checking premium in loadBannerAd: $e');
    }

    if (_isPremium) {
      appDebugLog('User has Premium - skipping banner ad');
      return;
    }

    // Skip rate limiting in debug mode for easier testing
    if (!kDebugMode) {
      if (_totalAdRequestsThisSession >= _maxRequestsPerSession) {
        appDebugLog(
          'AdMob session limit reached ($_maxRequestsPerSession requests) - skipping',
        );
        return;
      }

      final now = DateTime.now();
      if (_lastAdRequestTime != null &&
          now.difference(_lastAdRequestTime!).inSeconds < 30) {
        appDebugLog('AdMob throttled - wait 30 seconds between banner requests');
        return;
      }
    } else {
      appDebugLog('🧪 Debug mode - skipping ad rate limits');
    }

    if (!_isInitialized) {
      appDebugLog('AdMob not initialized yet - will retry banner load');
      Future.delayed(const Duration(seconds: 2), () {
        if (_isInitialized && !_isPremium && !_isBannerAdLoaded) {
          loadBannerAd(onLoaded: onLoaded);
        }
      });
      return;
    }

    if (_isBannerAdLoaded && _bannerAd != null) {
      appDebugLog('Banner ad already loaded');
      onLoaded?.call();
      return;
    }

    if (_bannerAd != null) {
      appDebugLog('Disposing existing banner before reload');
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
        appDebugLog('Using adaptive banner: ${adSize.width}x${adSize.height}');
      } else {
        appDebugLog(
          '⚠️ Adaptive size invalid (height=${adaptiveSize?.height}), using standard banner',
        );
      }
    } else {
      appDebugLog(
        '⚠️ Screen width invalid ($screenWidth), using standard banner',
      );
    }
    appDebugLog('Final banner ad size: ${adSize.width}x${adSize.height}');

    _bannerAd = BannerAd(
      adUnitId: bannerAdUnitId,
      size: adSize,
      request: const AdRequest(),
      listener: BannerAdListener(
        onAdLoaded: (ad) {
          if (_isPremium) {
            appDebugLog('User became Premium - disposing banner');
            ad.dispose();
            _isBannerAdLoaded = false;
            _notifyBannerDisplayChanged();
            return;
          }
          appDebugLog('Banner ad loaded successfully');
          _isBannerAdLoaded = true;
          _bannerRetryCount = 0;
          _lastError = '';
          onLoaded?.call();
          _notifyBannerDisplayChanged();
        },
        onAdFailedToLoad: (ad, error) {
          appDebugLog('Banner ad failed to load: $error');
          _lastError = error.toString();
          ad.dispose();
          _bannerAd = null;
          _isBannerAdLoaded = false;
          _notifyBannerDisplayChanged();
          _bannerRetryCount++;
          if (_bannerRetryCount <= 3 &&
              _totalAdRequestsThisSession < _maxRequestsPerSession) {
            appDebugLog(
              'Banner retry #$_bannerRetryCount scheduled in 60s (max 3)',
            );
            Future.delayed(const Duration(seconds: 60), () {
              if (!_isPremium && !_isBannerAdLoaded) {
                appDebugLog('Retrying banner ad load...');
                loadBannerAd(onLoaded: onLoaded);
              }
            });
          } else {
            appDebugLog(
              'Banner retry limit reached. No more retries this session.',
            );
          }
        },
        onAdOpened: (ad) => appDebugLog('Banner ad opened'),
        onAdClosed: (ad) => appDebugLog('Banner ad closed'),
      ),
    );
    _bannerAd!.load();
  }

  void disposeBannerAd() {
    _bannerAd?.dispose();
    _bannerAd = null;
    _isBannerAdLoaded = false;
    _notifyBannerDisplayChanged();
  }

  void dispose() {
    _appOpenPreloadAfterCooldownTimer?.cancel();
    _appOpenPreloadAfterCooldownTimer = null;
    WidgetsBinding.instance.removeObserver(this);
    _bannerAd?.dispose();
    _disposeInterstitialAd();
    _disposeRewardedAd();
    _appOpenAd?.dispose();
  }

  /// iOS: ATT одразу перед UMP / MobileAds (не блокуємо PurchaseService у main).
  Future<void> _ensureIosAttBeforeMobileAds() async {
    if (kIsWeb || !Platform.isIOS) return;
    try {
      var status =
          _trackingStatus ?? await AppTrackingTransparency.trackingAuthorizationStatus;
      appDebugLog('ATT before MobileAds: $status');
      if (status == TrackingStatus.notDetermined) {
        await Future.delayed(const Duration(milliseconds: 400));
        status = await AppTrackingTransparency.requestTrackingAuthorization();
        appDebugLog('ATT result: $status');
      }
      _trackingStatus = status;
      if (status == TrackingStatus.authorized) {
        try {
          final idfa = await AppTrackingTransparency.getAdvertisingIdentifier();
          appDebugLog('IDFA available: ${idfa.isNotEmpty}');
        } catch (e) {
          appDebugLog('IDFA read error: $e');
        }
      }
    } catch (e) {
      appDebugLog('ATT before MobileAds error: $e');
    }
  }

  // --- UMP. У debug форма згоди на симуляторі часто блокує WebView / main thread.
  Future<void> _gatherConsentForAds() async {
    if (kIsWeb) return;
    if (kDebugMode) {
      appDebugLog('UMP: skipped in debug — test consent in Profile/Release');
      return;
    }
    try {
      final done = Completer<void>();
      void safeComplete() {
        if (!done.isCompleted) done.complete();
      }

      ConsentInformation.instance.requestConsentInfoUpdate(
        ConsentRequestParameters(),
        () {
          ConsentForm.loadAndShowConsentFormIfRequired((formError) {
            if (formError != null) {
              appDebugLog('UMP form error: ${formError.message}');
            }
          }).whenComplete(safeComplete);
        },
        (error) {
          appDebugLog('UMP consent update failed: ${error.message}');
          safeComplete();
        },
      );

      await Future.any<void>([
        done.future,
        Future<void>.delayed(const Duration(seconds: 8)),
      ]);
      if (!done.isCompleted) {
        appDebugLog('UMP:8s cap — continuing with MobileAds init');
        safeComplete();
      }
    } catch (e) {
      appDebugLog('UMP exception: $e');
    }
  }

  // --- Interstitial (основний таб-бар) ---
  void onMainShellTabChanged({required int fromIndex, required int toIndex}) {
    if (fromIndex == toIndex) return;
    if (_isPremium || isAdFree || !_isInitialized) {
      if (_isPremium || isAdFree) {
        _logInterstitialDiag('tab change: skip (premium or ad-free)');
      } else if (!_isInitialized) {
        _logInterstitialDiag('tab change: skip (ads not initialized)');
      }
      return;
    }
    // Не перериваємо вхід у чат повноекранною рекламою.
    if (toIndex == 2) {
      _logInterstitialDiag('tab change: skip (entering chat tab)');
      return;
    }
    unawaited(() async {
      await _ensurePremiumFromPrefs();
      if (_isPremium || isAdFree) return;
      await _maybeShowInterstitialOnTabChange();
    }());
  }

  void _disposeInterstitialAd() {
    _interstitialRetryTimer?.cancel();
    _interstitialRetryTimer = null;
    _interstitialLoadRetryCount = 0;
    _interstitialAd?.dispose();
    _interstitialAd = null;
    _interstitialLoadInFlight = false;
  }

  Future<void> _preloadInterstitialAd() async {
    if (_isPremium || isAdFree || kIsWeb) return;
    final unitId = interstitialAdUnitId;
    if (unitId.isEmpty) return;
    if (_interstitialAd != null || _interstitialLoadInFlight) return;
    if (_interstitialShowsSession >= _maxInterstitialPerSession) return;
    _interstitialLoadInFlight = true;
    try {
      await InterstitialAd.load(
        adUnitId: unitId,
        request: const AdRequest(),
        adLoadCallback: InterstitialAdLoadCallback(
          onAdLoaded: (ad) {
            _interstitialLoadInFlight = false;
            _interstitialLoadRetryCount = 0;
            if (_isPremium || isAdFree) {
              ad.dispose();
              return;
            }
            _interstitialAd = ad;
            appDebugLog('Interstitial loaded');
            if (!kDebugMode) {
              _logAdsRelease('Interstitial loaded OK (unit=$unitId)');
            }
          },
          onAdFailedToLoad: (error) {
            _interstitialLoadInFlight = false;
            appDebugLog('Interstitial failed to load: $error');
            _logAdsRelease(
              'Interstitial LOAD FAILED code=${error.code} domain=${error.domain} '
              'message=${error.message} unit=$unitId',
            );
            _scheduleInterstitialReloadBackoff(unitId);
          },
        ),
      );
    } catch (e) {
      _interstitialLoadInFlight = false;
      appDebugLog('Interstitial load exception: $e');
    }
  }

  Future<void> _maybeShowInterstitialOnTabChange() async {
    await _ensurePremiumFromPrefs();
    if (_isPremium || isAdFree || _interstitialShowInProgress) return;
    if (_monetizationReadyAt == null) {
      _logInterstitialDiag('interstitial: skip (monetizationReadyAt null)');
      return;
    }
    final minForeground = _interstitialRelaxed
        ? const Duration(seconds: 2)
        : _minForegroundBeforeInterstitial;
    final minAfterAppOpen = _interstitialRelaxed
        ? const Duration(seconds: 6)
        : _minGapAfterAppOpenForInterstitial;
    final minBetween = _interstitialRelaxed
        ? const Duration(seconds: 10)
        : _interstitialMinInterval;

    final sinceReady = DateTime.now().difference(_monetizationReadyAt!);
    if (sinceReady < minForeground) {
      _logInterstitialDiag(
        'interstitial: skip (only ${sinceReady.inSeconds}s since ads ready, need ${minForeground.inSeconds}s)',
      );
      return;
    }
    if (_interstitialShowsSession >= _maxInterstitialPerSession) return;

    final prefs = await SharedPreferences.getInstance();
    final now = DateTime.now();
    final lastIn = prefs.getInt(_lastInterstitialShownKey);
    if (lastIn != null) {
      final lastInTime = DateTime.fromMillisecondsSinceEpoch(lastIn);
      final gap = now.difference(lastInTime);
      if (gap < minBetween) {
        _logInterstitialDiag(
          'interstitial: skip (${gap.inSeconds}s since last, need ${minBetween.inSeconds}s)',
        );
        return;
      }
    }
    final lastOpen = prefs.getInt(_lastAppOpenShowKey);
    if (lastOpen != null) {
      final lastOpenTime = DateTime.fromMillisecondsSinceEpoch(lastOpen);
      final gap = now.difference(lastOpenTime);
      if (gap < minAfterAppOpen) {
        _logInterstitialDiag(
          'interstitial: skip (${gap.inSeconds}s since app open ad, need ${minAfterAppOpen.inSeconds}s)',
        );
        return;
      }
    }

    // In debug mode UMP is skipped entirely so canRequestAds() is always false —
    // bypass the check to allow interstitial testing without triggering consent flow.
    if (!kDebugMode && !_interstitialRelaxed) {
      final canRequest = await ConsentInformation.instance.canRequestAds();
      if (!canRequest) {
        _logAdsRelease(
          'Interstitial SHOW skipped: canRequestAds=false (UMP / GDPR — перевір згоду)',
        );
        return;
      }
    }

    if (_interstitialAd == null) {
      await _preloadInterstitialAd();
      if (_interstitialAd == null) {
        _logInterstitialDiag('interstitial: skip (no ad loaded)');
        return;
      }
    }

    final ad = _interstitialAd!;
    _interstitialAd = null;
    _interstitialShowInProgress = true;

    ad.fullScreenContentCallback = FullScreenContentCallback<InterstitialAd>(
      onAdShowedFullScreenContent: (ad) {
        appDebugLog('Interstitial showed');
        unawaited(_recordInterstitialShown());
      },
      onAdDismissedFullScreenContent: (ad) {
        _interstitialShowInProgress = false;
        ad.dispose();
        unawaited(_preloadInterstitialAd());
      },
      onAdFailedToShowFullScreenContent: (ad, error) {
        _interstitialShowInProgress = false;
        appDebugLog('Interstitial failed to show: $error');
        ad.dispose();
        unawaited(_preloadInterstitialAd());
      },
    );

    try {
      await ad.show();
    } catch (e) {
      _interstitialShowInProgress = false;
      appDebugLog('Interstitial show error: $e');
      unawaited(_preloadInterstitialAd());
    }
  }

  Future<void> _recordInterstitialShown() async {
    _interstitialShowsSession++;
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setInt(
        _lastInterstitialShownKey,
        DateTime.now().millisecondsSinceEpoch,
      );
    } catch (e) {
      appDebugLog('Failed to record interstitial timestamp: $e');
    }
  }

  void _disposeRewardedAd() {
    _rewardedAd?.dispose();
    _rewardedAd = null;
    _rewardedLoadInFlight = false;
  }

  Future<void> _preloadRewardedAd() async {
    if (_isPremium || isAdFree || kIsWeb || !_isInitialized) return;
    final unitId = rewardedAdUnitId;
    if (unitId.isEmpty) return;
    if (_rewardedAd != null || _rewardedLoadInFlight) return;
    _rewardedLoadInFlight = true;
    try {
      await RewardedAd.load(
        adUnitId: unitId,
        request: const AdRequest(),
        rewardedAdLoadCallback: RewardedAdLoadCallback(
          onAdLoaded: (ad) {
            _rewardedLoadInFlight = false;
            if (_isPremium || isAdFree) {
              ad.dispose();
              return;
            }
            _rewardedAd = ad;
            appDebugLog('Rewarded ad loaded');
          },
          onAdFailedToLoad: (error) {
            _rewardedLoadInFlight = false;
            appDebugLog('Rewarded failed to load: $error');
          },
        ),
      );
    } catch (e) {
      _rewardedLoadInFlight = false;
      appDebugLog('Rewarded load exception: $e');
    }
  }

  /// Тимчасово прибирає банер і повноекранну рекламу (див. [isAdFree]).
  Future<void> grantAdFreeBonus(Duration duration) async {
    if (_isPremium) return;
    final until = DateTime.now().add(duration);
    _adFreeUntil = until;
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setInt(_adFreeUntilKey, until.millisecondsSinceEpoch);
    } catch (e) {
      appDebugLog('grantAdFreeBonus: $e');
    }
    disposeBannerAd();
    _disposeInterstitialAd();
    _disposeRewardedAd();
    _notifyBannerDisplayChanged();
    appDebugLog('Ad-free bonus until $until');
  }

  /// Показ rewarded; винагорода приходить лише після підтвердження з боку мережі.
  Future<bool> showRewardedAd({
    required OnUserEarnedRewardCallback onUserEarnedReward,
  }) async {
    await _ensurePremiumFromPrefs();
    if (_isPremium || kIsWeb || !_isInitialized) return false;
    if (isAdFree) {
      appDebugLog('Rewarded skip: ad-free active');
      return false;
    }
    if (!kDebugMode && !_interstitialRelaxed) {
      final canRequest = await ConsentInformation.instance.canRequestAds();
      if (!canRequest) return false;
    }

    if (_rewardedAd == null) {
      await _preloadRewardedAd();
    }
    if (_rewardedAd == null) return false;

    final ad = _rewardedAd!;
    _rewardedAd = null;

    ad.fullScreenContentCallback = FullScreenContentCallback<RewardedAd>(
      onAdDismissedFullScreenContent: (a) {
        a.dispose();
        unawaited(_preloadRewardedAd());
      },
      onAdFailedToShowFullScreenContent: (a, error) {
        appDebugLog('Rewarded failed to show: $error');
        a.dispose();
        unawaited(_preloadRewardedAd());
      },
    );

    try {
      await ad.show(onUserEarnedReward: onUserEarnedReward);
      return true;
    } catch (e) {
      appDebugLog('Rewarded show error: $e');
      unawaited(_preloadRewardedAd());
      return false;
    }
  }

  /// Перегляд відео → 1 год без реклами (банер, app open, interstitial).
  Future<bool> showRewardedForOneHourAdFree() {
    return showRewardedAd(
      onUserEarnedReward: (ad, reward) {
        appDebugLog('Reward earned: ${reward.type} × ${reward.amount}');
        unawaited(grantAdFreeBonus(const Duration(hours: 1)));
      },
    );
  }

  /// One request after inter-show cooldown — avoids loading while the next show
  /// is impossible, but keeps an ad warm if the user stays in the app.
  void _scheduleAppOpenPreloadAfterCooldown() {
    if (_isPremium || isAdFree) return;
    _appOpenPreloadAfterCooldownTimer?.cancel();
    _appOpenPreloadAfterCooldownTimer = Timer(_appOpenCooldown, () {
      _appOpenPreloadAfterCooldownTimer = null;
      if (_isPremium || isAdFree) return;
      unawaited(_loadAppOpenAdSilently());
    });
  }

  // ============== iOS App Tracking Transparency ==============
  // Запит ATT — у [_ensureIosAttBeforeMobileAds].

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
