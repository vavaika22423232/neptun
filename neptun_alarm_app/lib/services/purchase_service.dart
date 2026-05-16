import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:in_app_purchase/in_app_purchase.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:http/http.dart' as http;
import 'ad_service.dart';
import 'widget_service.dart';
import 'alarm_tracking_service.dart';
import 'auth_service.dart';
import 'package:neptun_alarm_app/config/api_config.dart';
import 'package:neptun_alarm_app/config/prefs_keys.dart';

void _iapDebug(String message) {
  if (kDebugMode) debugPrint(message);
}

enum _EntitlementBindResult {
  success,
  noCredentials,
  transientFailure,
  deniedByServer,
}

enum AppTier { free, pro }

class PurchaseService {
  static final PurchaseService _instance = PurchaseService._internal();
  factory PurchaseService() => _instance;
  PurchaseService._internal();

  final InAppPurchase _inAppPurchase = InAppPurchase.instance;
  StreamSubscription<List<PurchaseDetails>>? _subscription;

  // ── SKU ───────────────────────────────────────────────────────────────────
  /// Pro-підписка (місячна) — основний продукт.
  static const String proMonthlyId = 'pro_monthly';
  /// Pro legacy — одноразова покупка (старі користувачі).
  static const String proForeverId = 'premium_150_uah';

  // Старі legacy IDs → той самий рівень Pro.
  static const Set<String> _legacyProIds = {
    'premium_100_uah',
    'premium',
    'com.neptunalarm.premium',
  };

  static const Set<String> _proIds = {proMonthlyId, proForeverId};

  static Set<String> get _allKnownIds => {..._proIds, ..._legacyProIds};

  static const String _skProductId = 'iap_premium_product_id';
  static const String _skToken     = 'iap_premium_token';
  static const String _skSource    = 'iap_premium_source';

  /// Prefs key для збереження тарифу між сесіями.
  static const String _tierPrefKey = 'active_tier';

  static const FlutterSecureStorage _iapSecure = FlutterSecureStorage(
    aOptions: AndroidOptions(encryptedSharedPreferences: true),
    iOptions: IOSOptions(
      accessibility: KeychainAccessibility.first_unlock,
      accountName: 'com.neptunalarm.neptunAlarmApp.iap',
    ),
  );

  bool get _useIapSecureStorage => !kIsWeb && !(kDebugMode && Platform.isIOS);

  List<ProductDetails> products = [];
  bool _isPremium = false;
  bool _debugOverride = false;
  AppTier _tier = AppTier.free;

  bool get isPremium => _isPremium || _debugOverride;

  /// Поточний тариф. Legacy-покупці → [AppTier.pro].
  AppTier get tier {
    if (_debugOverride) return AppTier.pro;
    return _tier;
  }

  // Кеш останньої перевірки (щоб не перевіряти занадто часто)
  DateTime? _lastVerificationTime;
  static const Duration _verificationCooldown = Duration(hours: 1);

  // Notifier для UI
  final ValueNotifier<bool> premiumNotifier = ValueNotifier(false);
  /// Сповіщає UI про зміну тарифу.
  final ValueNotifier<AppTier> tierNotifier = ValueNotifier(AppTier.free);

  // Callbacks
  Function()? onPurchaseSuccess;
  Function(String error)? onPurchaseError;

  /// Force-enable premium in debug builds (IAP unavailable or manual testing).
  Future<void> enableDebugPremium() async {
    _debugOverride = true;
    premiumNotifier.value = true;
    AdService().setPremiumStatus(true);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('debug_premium', true);
    _iapDebug('🌟 Debug premium enabled');
  }

  /// Clears debug PRO override and stale `debug_premium` prefs (e.g. after old simulator auto-PRO).
  /// Keeps real entitlement from `is_premium` only.
  Future<void> disableDebugPremium() async {
    _debugOverride = false;
    final prefs = await SharedPreferences.getInstance();
    if (prefs.containsKey('debug_premium')) {
      await prefs.remove('debug_premium');
      _iapDebug('🧹 Removed debug_premium from prefs');
    }
    premiumNotifier.value = _isPremium;
    AdService().setPremiumStatus(_isPremium);
  }

  Future<void> initialize() async {
    final prefs = await SharedPreferences.getInstance();

    // Завантажуємо локальний статус одразу — щоб платні користувачі бачили premium
    await _loadLocalPremiumStatus();

    // Уникнути подвійної підписки (hot restart / повторний init).
    await _subscription?.cancel();
    _subscription = null;

    try {
      final bool available = await _inAppPurchase.isAvailable();
      if (!available) {
        _iapDebug('In-app purchases not available');
        // На симуляторі IAP часто недоступний — не return, щоб дійти до debug PRO.
      } else {
        // Listen to purchase updates
        _subscription = _inAppPurchase.purchaseStream.listen(
          _onPurchaseUpdate,
          onDone: () => _subscription?.cancel(),
          onError: (error) => _iapDebug('Purchase stream error: $error'),
        );

        // Load products
        await loadProducts();

        // ЗАХИСТ ВІД LUCKY PATCHER — не блокуємо cold start / splash: StoreKit restore
        // може довго відповідати або «зависати» на деяких збірках.
        unawaited(_verifyPurchasesFromStore());
      }
    } catch (e) {
      _iapDebug('In-app purchases initialization error: $e');
      // При помилці НЕ скидаємо — зберігаємо локальний статус (сервер/мережа могли бути тимчасово недоступні)
    }

    // Серверний entitlement: знімає фейковий is_premium без валідного токена (Android онлайн)
    await _syncEntitlementWithServer();

    await _applyDebugPremiumIfNeeded(prefs);
  }

  /// У debug: фейковий PRO **лише** за `--dart-define=NEPTUN_DEBUG_PRO=true`.
  /// Прапорець `debug_premium` у prefs більше не вмикає PRO автоматично (щоб не «липнути»
  /// після старого авто-PRO на симуляторі) — його прибираємо, якщо define вимкнено.
  Future<void> _applyDebugPremiumIfNeeded(SharedPreferences prefs) async {
    if (!kDebugMode) return;
    const fromDefine =
        bool.fromEnvironment('NEPTUN_DEBUG_PRO', defaultValue: false);
    if (!fromDefine) {
      await disableDebugPremium();
      return;
    }
    await enableDebugPremium();
    _iapDebug('🌟 Debug PRO: NEPTUN_DEBUG_PRO=true');
  }

  /// ЗАХИСТ: Перевірка покупок безпосередньо з Google Play Store
  /// Lucky Patcher не може підробити відповідь від Google серверів
  Future<void> _verifyPurchasesFromStore() async {
    try {
      // Перевіряємо чи минув cooldown
      if (_lastVerificationTime != null &&
          DateTime.now().difference(_lastVerificationTime!) <
              _verificationCooldown) {
        _iapDebug('⏭️ Skipping verification (cooldown active)');
        return;
      }

      _iapDebug(
        '🔐 Verifying purchases from ${(!kIsWeb && Platform.isIOS) ? "App Store" : "Google Play"}...',
      );

      // Відновлюємо покупки — з таймаутом (StoreKit інколи довго не відповідає).
      try {
        await _inAppPurchase
            .restorePurchases()
            .timeout(const Duration(seconds: 30));
      } on TimeoutException {
        _iapDebug('restorePurchases() timed out after 30s');
      }

      // Швидший полінг на старті — не блокувати AdMob/інший init на 8+ сек
      for (var i = 0; i < 12; i++) {
        await Future.delayed(const Duration(milliseconds: 350));
        if (_isPremium) break;
      }

      if (_isPremium) {
        _iapDebug('✅ Premium verified successfully');
      } else {
        // НЕ скидаємо Premium — магазин міг не відповісти вчасно,
        // або покупка була на іншому акаунті. Зберігаємо локальний статус.
        _iapDebug('⚠️ No purchases in store response — keeping local status');
      }

      _lastVerificationTime = DateTime.now();
    } catch (e) {
      _iapDebug('Verification error: $e');
      // При помилці НЕ скидаємо — залишаємо локальний статус (мережа/сервер могли бути недоступні)
    }
  }

  Future<void> _loadLocalPremiumStatus() async {
    final prefs = await SharedPreferences.getInstance();
    _isPremium = prefs.getBool('is_premium') ?? false;
    _tier = _tierFromString(prefs.getString(_tierPrefKey));
    // Migration: legacy purchases without tier key → Pro
    if (_isPremium && _tier == AppTier.free) {
      _tier = AppTier.pro;
      await prefs.setString(_tierPrefKey, _tierToString(_tier));
    }
    premiumNotifier.value = _isPremium;
    tierNotifier.value = _tier;

    if (_isPremium) {
      AdService().setPremiumStatus(true);
    }
  }

  static AppTier _tierFromString(String? value) {
    switch (value) {
      case 'pro':   return AppTier.pro;
      default:      return AppTier.free;
    }
  }

  static String _tierToString(AppTier t) {
    switch (t) {
      case AppTier.pro:  return 'pro';
      case AppTier.free: return 'free';
    }
  }

  AppTier _tierForProductId(String productId) {
    if (_proIds.contains(productId) || _legacyProIds.contains(productId)) {
      return AppTier.pro;
    }
    return AppTier.free;
  }

  Future<void> _writeIapSecure(String key, String value) async {
    if (_useIapSecureStorage) {
      await _iapSecure.write(key: key, value: value);
    } else {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('_iap_fb_$key', value);
    }
  }

  Future<String?> _readIapSecure(String key) async {
    if (_useIapSecureStorage) {
      return _iapSecure.read(key: key);
    }
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString('_iap_fb_$key');
  }

  Future<void> _deleteIapSecure(String key) async {
    if (_useIapSecureStorage) {
      await _iapSecure.delete(key: key);
    } else {
      final prefs = await SharedPreferences.getInstance();
      await prefs.remove('_iap_fb_$key');
    }
  }

  Future<void> _persistIapCredentials(PurchaseDetails d) async {
    final vd = d.verificationData;
    final token = vd.serverVerificationData;
    if (token.isEmpty) return;
    await _writeIapSecure(_skProductId, d.productID);
    await _writeIapSecure(_skToken, token);
    await _writeIapSecure(_skSource, vd.source);
  }

  Future<void> _clearIapCredentials() async {
    await _deleteIapSecure(_skProductId);
    await _deleteIapSecure(_skToken);
    await _deleteIapSecure(_skSource);
  }

  Future<bool> _hasIapCredentials() async {
    final t = await _readIapSecure(_skToken);
    final p = await _readIapSecure(_skProductId);
    return p != null &&
        p.isNotEmpty &&
        t != null &&
        t.isNotEmpty;
  }

  Future<bool> _isOnline() async {
    try {
      final r = await Connectivity().checkConnectivity();
      return r.any((c) => c != ConnectivityResult.none);
    } catch (_) {
      return true;
    }
  }

  Future<_EntitlementBindResult> _postEntitlementRegisterDetailed(
    String deviceId,
    String productId,
    String purchaseToken,
    String source,
  ) async {
    try {
      final res = await http
          .post(
            Uri.parse(ApiConfig.premiumEntitlement),
            headers: {'Content-Type': 'application/json'},
            body: json.encode({
              'deviceId': deviceId,
              'productId': productId,
              'purchaseToken': purchaseToken,
              'source': source,
            }),
          )
          .timeout(const Duration(seconds: 22));
      if (res.statusCode == 503 ||
          res.statusCode == 502 ||
          res.statusCode == 504 ||
          res.statusCode >= 500) {
        return _EntitlementBindResult.transientFailure;
      }
      if (res.statusCode != 200) {
        return _EntitlementBindResult.transientFailure;
      }
      final data = json.decode(res.body) as Map<String, dynamic>?;
      if (data?['ok'] == true) return _EntitlementBindResult.success;
      if (data?['pending'] == true) {
        return _EntitlementBindResult.transientFailure;
      }
      return _EntitlementBindResult.deniedByServer;
    } catch (e) {
      _iapDebug('Entitlement POST error: $e');
      return _EntitlementBindResult.transientFailure;
    }
  }

  Future<bool> _postEntitlementRegister(
    String deviceId,
    String productId,
    String purchaseToken,
    String source,
  ) async {
    final r = await _postEntitlementRegisterDetailed(
      deviceId,
      productId,
      purchaseToken,
      source,
    );
    return r == _EntitlementBindResult.success;
  }

  /// Реєстрація покупки на сервері + синхронізація з Redis entitlement.
  Future<void> _registerEntitlementWithServer(PurchaseDetails d) async {
    final deviceId = await AuthService.getDeviceId();
    final vd = d.verificationData;
    final token = vd.serverVerificationData;
    if (token.isEmpty) return;
    final ok = await _postEntitlementRegister(
      deviceId,
      d.productID,
      token,
      vd.source,
    );
    if (ok) {
      _iapDebug('✅ Server entitlement registered');
    } else {
      _iapDebug('⚠️ Server entitlement register failed (will retry on next sync)');
    }
  }

  Future<void> _revokePremiumLocal() async {
    await _clearIapCredentials();
    await _savePremiumStatus(false, newTier: AppTier.free);
    _iapDebug('🔒 Pro revoked (server entitlement check)');
  }

  /// Підтягує Pro з сервера після перевстановлення; знімає фейковий Pro без токена.
  Future<void> _syncEntitlementWithServer() async {
    if (kIsWeb) return;
    if (!Platform.isAndroid && !Platform.isIOS) return;

    final deviceId = await AuthService.getDeviceId();
    final uri = Uri.parse(ApiConfig.premiumEntitlement).replace(
      queryParameters: {'deviceId': deviceId},
    );

    try {
      final getRes =
          await http.get(uri).timeout(const Duration(seconds: 22));
      if (getRes.statusCode != 200) {
        _iapDebug('⚠️ Entitlement GET ${getRes.statusCode}, keep local state');
        return;
      }

      final gd = json.decode(getRes.body) as Map<String, dynamic>?;

      if (gd?['entitled'] == true) {
        if (!_isPremium) {
          _iapDebug('✅ Pro granted from server entitlement (reinstall)');
          await _savePremiumStatus(true);
        }
        return;
      }

      if (gd?['revoked'] == true) {
        await _revokePremiumLocal();
        return;
      }

      if (gd?['noBinding'] == true && _isPremium) {
        final bind = await _tryBindEntitlementFromStored(deviceId);
        if (bind == _EntitlementBindResult.success) return;
        if (bind == _EntitlementBindResult.transientFailure) return;

        if (await _hasIapCredentials()) {
          if (!kIsWeb &&
              Platform.isAndroid &&
              await _isOnline() &&
              bind == _EntitlementBindResult.deniedByServer) {
            await _revokePremiumLocal();
          }
          return;
        }

        if (!kIsWeb && Platform.isAndroid && await _isOnline()) {
          await _revokePremiumLocal();
        }
        return;
      }
    } catch (e) {
      _iapDebug('⚠️ Entitlement sync skipped (network): $e');
    }
  }

  Future<_EntitlementBindResult> _tryBindEntitlementFromStored(
    String deviceId,
  ) async {
    final pid = await _readIapSecure(_skProductId);
    final tok = await _readIapSecure(_skToken);
    final src = await _readIapSecure(_skSource) ?? '';
    if (pid == null || tok == null || tok.isEmpty) {
      return _EntitlementBindResult.noCredentials;
    }
    final r = await _postEntitlementRegisterDetailed(
      deviceId,
      pid,
      tok,
      src,
    );
    if (r == _EntitlementBindResult.success) {
      _iapDebug('✅ Entitlement bound from stored IAP credentials');
    }
    return r;
  }

  Future<void> loadProducts() async {
    try {
      final ProductDetailsResponse response = await _inAppPurchase
          .queryProductDetails(_allKnownIds)
          .timeout(const Duration(seconds: 25));

      if (response.notFoundIDs.isNotEmpty) {
        _iapDebug('Products not found: ${response.notFoundIDs}');
      }

      products = response.productDetails;
      _iapDebug('Loaded ${products.length} products');

      for (final product in products) {
        _iapDebug('Product: ${product.id} - ${product.price}');
      }
    } on TimeoutException {
      _iapDebug('queryProductDetails timed out — store slow or offline');
      products = [];
    }
  }

  Future<void> _saveTier(AppTier newTier) async {
    _tier = newTier;
    tierNotifier.value = newTier;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_tierPrefKey, _tierToString(newTier));
  }

  Future<void> _savePremiumStatus(bool value, {AppTier? newTier}) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('is_premium', value);
    _isPremium = value;
    if (newTier != null) await _saveTier(newTier);
    premiumNotifier.value = value;

    // Update AdService
    AdService().setPremiumStatus(value);

    if (value) {
      _iapDebug('🌟 Premium activated - ads disabled');

      // Оновити віджет після активації Premium
      try {
        final alarmService = AlarmTrackingService();
        final alarmData = await alarmService.getCurrentAlarmData();
        await WidgetService().updateWidget(
          region: alarmData['region'] as String? ?? 'Всі регіони',
          isAlarm: alarmData['isAlarm'] as bool? ?? false,
          threatsCount: alarmData['threatsCount'] as int? ?? 0,
          timerMinutes: alarmData['timerMinutes'] as int? ?? 0,
          totalAlarms: alarmData['totalAlarms'] as int? ?? 0,
          threatType: alarmData['threatType'] as String? ?? '',
          dronesCount: alarmData['dronesCount'] as int? ?? 0,
          missilesCount: alarmData['missilesCount'] as int? ?? 0,
          kabCount: alarmData['kabCount'] as int? ?? 0,
          ballisticCount: alarmData['ballisticCount'] as int? ?? 0,
          totalThreats: alarmData['totalThreats'] as int? ?? 0,
        );
        _iapDebug('✅ Widget updated after Premium activation');
      } catch (e) {
        _iapDebug('⚠️ Failed to update widget after Premium activation: $e');
      }
    } else {
      _iapDebug('Premium deactivated - ads enabled');
      final sound = prefs.getString(PrefsKeys.alarmSoundId) ?? 'default';
      if (sound == 'sharp' || sound == 'siren') {
        await prefs.setString(PrefsKeys.alarmSoundId, 'default');
      }
      try {
        await WidgetService().applyNonPremiumWidgetState();
      } catch (_) {}
    }
  }

  void _onPurchaseUpdate(List<PurchaseDetails> purchaseDetailsList) {
    // Послідовна обробка: паралельні _handlePurchase ламали порядок completePurchase на iOS.
    unawaited(_processPurchaseBatch(purchaseDetailsList));
  }

  Future<void> _processPurchaseBatch(List<PurchaseDetails> batch) async {
    for (final purchaseDetails in batch) {
      await _handlePurchase(purchaseDetails);
    }
  }

  Future<void> _handlePurchase(PurchaseDetails purchaseDetails) async {
    if (purchaseDetails.status == PurchaseStatus.pending) {
      _iapDebug('Purchase pending...');
    } else if (purchaseDetails.status == PurchaseStatus.error) {
      final msg = purchaseDetails.error?.message ?? 'Unknown error';
      _iapDebug('Purchase error: $msg');
      // itemAlreadyOwned / "Цей елемент уже ваш" — користувач вже має покупку
      if (_isAlreadyOwnedError(msg)) {
        _iapDebug('✅ Already owned — activating premium');
        await _savePremiumStatus(true);
        await _inAppPurchase.restorePurchases();
        onPurchaseSuccess?.call();
      } else {
        onPurchaseError?.call(msg);
      }
    } else if (purchaseDetails.status == PurchaseStatus.purchased ||
        purchaseDetails.status == PurchaseStatus.restored) {
      // Тільки наші продукти
      if (!_allKnownIds.contains(purchaseDetails.productID)) {
        _iapDebug('Ignore unknown product: ${purchaseDetails.productID}');
        if (purchaseDetails.pendingCompletePurchase) {
          await _inAppPurchase.completePurchase(purchaseDetails);
        }
        return;
      }

      if (purchaseDetails.status == PurchaseStatus.restored) {
        _iapDebug('✅ Purchase restored from store: ${purchaseDetails.productID}');
        await _deliverProduct(purchaseDetails);
        onPurchaseSuccess?.call();
      } else {
        final isValid = await _verifyPurchaseOnServer(purchaseDetails);
        if (isValid) {
          _iapDebug('✅ Purchase verified: ${purchaseDetails.productID}');
          await _deliverProduct(purchaseDetails);
          onPurchaseSuccess?.call();
        } else {
          _iapDebug('❌ Purchase verification FAILED: ${purchaseDetails.productID}');
          onPurchaseError?.call('Не вдалося підтвердити покупку');
        }
      }
    } else if (purchaseDetails.status == PurchaseStatus.canceled) {
      _iapDebug('Purchase canceled');
      onPurchaseError?.call('Покупку скасовано');
    }

    // Complete the purchase (важливо!)
    if (purchaseDetails.pendingCompletePurchase) {
      await _inAppPurchase.completePurchase(purchaseDetails);
    }
  }

  /// Верифікація покупки на нашому сервері
  /// Сервер перевіряє токен через Google Play Developer API / Apple receipt verification.
  ///
  /// Якщо сервер перевантажений (502/503/504) або Google ще в статусі pending — ретраї з backoff.
  /// Після вичерпання ретраїв з **тискучими** помилками довіряємо магазину: платіж уже в стані
  /// [PurchaseStatus.purchased], інакше користувач залишається без Pro після списання.
  Future<bool> _verifyPurchaseOnServer(PurchaseDetails purchaseDetails) async {
    const maxRetries = 5;
    final verificationData = purchaseDetails.verificationData;
    var sawTransient = false;

    for (var attempt = 1; attempt <= maxRetries; attempt++) {
      try {
        final response = await http
            .post(
              Uri.parse(ApiConfig.verifyPurchase),
              headers: {'Content-Type': 'application/json'},
              body: json.encode({
                'productId': purchaseDetails.productID,
                'purchaseToken': verificationData.serverVerificationData,
                'source': verificationData.source,
              }),
            )
            .timeout(const Duration(seconds: 22));

        Map<String, dynamic>? data;
        try {
          final decoded = json.decode(response.body);
          if (decoded is Map<String, dynamic>) data = decoded;
        } catch (_) {
          data = null;
        }

        if (response.statusCode == 200 && data != null) {
          if (data['valid'] == true) return true;
          // Сервер просить повторити (pending у Google / transient у JSON — лише якщо колись додамо на 200)
          if (data['pending'] == true || data['transient'] == true) {
            sawTransient = true;
            _iapDebug(
              '⚠️ Verify pending/transient (attempt $attempt/$maxRetries)',
            );
            if (attempt < maxRetries) {
              await Future.delayed(Duration(milliseconds: 500 * attempt));
            }
            continue;
          }
          // Остаточна відмова (невалідний токен, скасована покупка)
          _iapDebug('❌ Verify rejected by server (definitive)');
          return false;
        }

        // Тимчасові збої: nginx, наш Node, rate limit
        if (response.statusCode == 503 ||
            response.statusCode == 502 ||
            response.statusCode == 504 ||
            response.statusCode == 429 ||
            response.statusCode >= 500) {
          sawTransient = true;
          _iapDebug(
            '⚠️ Verify HTTP ${response.statusCode} (attempt $attempt/$maxRetries)',
          );
          if (attempt < maxRetries) {
            await Future.delayed(Duration(milliseconds: 500 * attempt));
          }
          continue;
        }

        _iapDebug(
          '⚠️ Verify unexpected HTTP ${response.statusCode} (attempt $attempt/$maxRetries)',
        );
        if (attempt < maxRetries) {
          sawTransient = true;
          await Future.delayed(Duration(milliseconds: 500 * attempt));
        }
      } catch (e) {
        sawTransient = true;
        _iapDebug('Verification error: $e (attempt $attempt/$maxRetries)');
        if (attempt < maxRetries) {
          await Future.delayed(Duration(milliseconds: 500 * attempt));
        }
      }
    }

    if (sawTransient) {
      _iapDebug(
        '⚠️ Server could not confirm after $maxRetries attempts — trusting app store '
        '(${purchaseDetails.productID}, source=${verificationData.source})',
      );
      return true;
    }

    onPurchaseError?.call('Не вдалося перевірити покупку. Спробуйте пізніше.');
    return false;
  }

  Future<void> _deliverProduct(PurchaseDetails purchaseDetails) async {
    final newTier = _tierForProductId(purchaseDetails.productID);
    await _savePremiumStatus(true, newTier: newTier);
    AdService().setPremiumStatus(true);
    await _persistIapCredentials(purchaseDetails);
    await _registerEntitlementWithServer(purchaseDetails);
    _iapDebug(
      '🎉 Tier=${_tierToString(newTier)} activated for product: ${purchaseDetails.productID}',
    );
  }

  static bool _isAlreadyOwnedError(String message) {
    final lower = message.toLowerCase();
    return lower.contains('itemalreadyowned') ||
        lower.contains('item_already_owned') ||
        lower.contains('already yours') ||
        lower.contains('уже ваш') ||
        lower.contains('already owned');
  }

  /// Купити Pro-підписку (місячна) або legacy forever.
  Future<bool> buyTier(String productId) async {
    if (_isPremium) {
      onPurchaseSuccess?.call();
      return true;
    }
    if (products.isEmpty) await loadProducts();
    final ProductDetails? product =
        products.where((p) => p.id == productId).firstOrNull;
    if (product == null) {
      _iapDebug('Product $productId not found in store');
      onPurchaseError?.call(
        'Товар недоступний у магазині. Перевірте з\'єднання або оновіть додаток.',
      );
      return false;
    }
    final param = PurchaseParam(productDetails: product);
    // proMonthlyId — підписка (subscription), proForeverId — non-consumable (legacy)
    if (productId == proMonthlyId) {
      return _inAppPurchase.buyConsumable(purchaseParam: param);
    }
    return _inAppPurchase.buyNonConsumable(purchaseParam: param);
  }

  /// Купити Pro (одноразова покупка навжди).
  Future<bool> buyPremium() => buyTier(proForeverId);

  /// Відновити покупки (якщо перевстановив додаток).
  /// Чекає на відповідь з магазину та повертає true, якщо premium активовано.
  Future<bool> restorePurchases() async {
    await _inAppPurchase.restorePurchases();
    for (var i = 0; i < 14; i++) {
      await Future.delayed(const Duration(milliseconds: 350));
      if (_isPremium) return true;
    }
    return _isPremium;
  }

  void dispose() {
    _subscription?.cancel();
    premiumNotifier.dispose();
  }
}
