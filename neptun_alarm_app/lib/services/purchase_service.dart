import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:in_app_purchase/in_app_purchase.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:http/http.dart' as http;
import 'ad_service.dart';
import 'widget_service.dart';
import 'alarm_tracking_service.dart';
import 'package:neptun_alarm_app/config/api_config.dart';

class PurchaseService {
  static final PurchaseService _instance = PurchaseService._internal();
  factory PurchaseService() => _instance;
  PurchaseService._internal();

  final InAppPurchase _inAppPurchase = InAppPurchase.instance;
  StreamSubscription<List<PurchaseDetails>>? _subscription;

  // Product ID — основний продукт Premium 150 грн
  static const String _premiumProductId = 'premium_150_uah';

  // Legacy product IDs — для користувачів, що купили до зміни product ID
  static const Set<String> _premiumProductIds = {
    _premiumProductId,
    'premium_100_uah',
    'premium',
  };

  static const Set<String> _productIds = {_premiumProductId};

  List<ProductDetails> products = [];
  bool _isPremium = false;
  bool _debugOverride = false;
  bool get isPremium => _isPremium || _debugOverride;

  // Кеш останньої перевірки (щоб не перевіряти занадто часто)
  DateTime? _lastVerificationTime;
  static const Duration _verificationCooldown = Duration(hours: 1);

  // Notifier для UI
  final ValueNotifier<bool> premiumNotifier = ValueNotifier(false);

  // Callbacks
  Function()? onPurchaseSuccess;
  Function(String error)? onPurchaseError;

  /// Force-enable premium in debug builds (for simulators where IAP is unavailable).
  Future<void> enableDebugPremium() async {
    _debugOverride = true;
    premiumNotifier.value = true;
    AdService().setPremiumStatus(true);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('debug_premium', true);
    debugPrint('🌟 Debug premium enabled');
  }

  Future<void> initialize() async {
    // Debug premium disabled — do not restore (user requested no premium on emulator)
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('debug_premium');

    // Завантажуємо локальний статус одразу — щоб платні користувачі бачили premium
    await _loadLocalPremiumStatus();

    try {
      final bool available = await _inAppPurchase.isAvailable();
      if (!available) {
        debugPrint('In-app purchases not available');
        // Не скидаємо — зберігаємо локальний статус (користувач міг купити раніше)
        return;
      }

      // Listen to purchase updates
      _subscription = _inAppPurchase.purchaseStream.listen(
        _onPurchaseUpdate,
        onDone: () => _subscription?.cancel(),
        onError: (error) => debugPrint('Purchase stream error: $error'),
      );

      // Load products
      await loadProducts();

      // ЗАХИСТ ВІД LUCKY PATCHER: перевіряємо через Google Play / App Store
      await _verifyPurchasesFromStore();
    } catch (e) {
      debugPrint('In-app purchases initialization error: $e');
      // При помилці НЕ скидаємо — зберігаємо локальний статус (сервер/мережа могли бути тимчасово недоступні)
    }
  }

  /// ЗАХИСТ: Перевірка покупок безпосередньо з Google Play Store
  /// Lucky Patcher не може підробити відповідь від Google серверів
  Future<void> _verifyPurchasesFromStore() async {
    try {
      // Перевіряємо чи минув cooldown
      if (_lastVerificationTime != null &&
          DateTime.now().difference(_lastVerificationTime!) <
              _verificationCooldown) {
        debugPrint('⏭️ Skipping verification (cooldown active)');
        return;
      }

      debugPrint(
        '🔐 Verifying purchases from ${Platform.isIOS ? "App Store" : "Google Play"}...',
      );

      // Відновлюємо покупки - це отримує реальні дані з Google Play
      await _inAppPurchase.restorePurchases();

      // Чекаємо на purchaseStream (Google/Apple можуть відповідати 5–10 сек)
      for (var i = 0; i < 10; i++) {
        await Future.delayed(const Duration(milliseconds: 800));
        if (_isPremium) break;
      }

      if (_isPremium) {
        debugPrint('✅ Premium verified successfully');
      } else {
        // НЕ скидаємо Premium — магазин міг не відповісти вчасно,
        // або покупка була на іншому акаунті. Зберігаємо локальний статус.
        debugPrint('⚠️ No purchases in store response — keeping local status');
      }

      _lastVerificationTime = DateTime.now();
    } catch (e) {
      debugPrint('Verification error: $e');
      // При помилці НЕ скидаємо — залишаємо локальний статус (мережа/сервер могли бути недоступні)
    }
  }

  Future<void> _loadLocalPremiumStatus() async {
    final prefs = await SharedPreferences.getInstance();
    _isPremium = prefs.getBool('is_premium') ?? false;
    premiumNotifier.value = _isPremium;

    if (_isPremium) {
      AdService().setPremiumStatus(true);
    }
  }

  Future<void> loadProducts() async {
    final ProductDetailsResponse response = await _inAppPurchase
        .queryProductDetails(_productIds);

    if (response.notFoundIDs.isNotEmpty) {
      debugPrint('Products not found: ${response.notFoundIDs}');
    }

    products = response.productDetails;
    debugPrint('Loaded ${products.length} products');

    // Вивести інформацію про продукти
    for (final product in products) {
      debugPrint('Product: ${product.id} - ${product.price}');
    }
  }

  Future<void> _savePremiumStatus(bool value) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('is_premium', value);
    _isPremium = value;
    premiumNotifier.value = value;

    // Update AdService
    AdService().setPremiumStatus(value);

    if (value) {
      debugPrint('🌟 Premium activated - ads disabled');

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
        debugPrint('✅ Widget updated after Premium activation');
      } catch (e) {
        debugPrint('⚠️ Failed to update widget after Premium activation: $e');
      }
    } else {
      debugPrint('📢 Premium deactivated - ads enabled');
    }
  }

  void _onPurchaseUpdate(List<PurchaseDetails> purchaseDetailsList) {
    for (final purchaseDetails in purchaseDetailsList) {
      _handlePurchase(purchaseDetails);
    }
  }

  Future<void> _handlePurchase(PurchaseDetails purchaseDetails) async {
    if (purchaseDetails.status == PurchaseStatus.pending) {
      debugPrint('Purchase pending...');
    } else if (purchaseDetails.status == PurchaseStatus.error) {
      final msg = purchaseDetails.error?.message ?? 'Unknown error';
      debugPrint('Purchase error: $msg');
      // itemAlreadyOwned / "Цей елемент уже ваш" — користувач вже має покупку
      if (_isAlreadyOwnedError(msg)) {
        debugPrint('✅ Already owned — activating premium');
        await _savePremiumStatus(true);
        onPurchaseSuccess?.call();
      } else {
        onPurchaseError?.call(msg);
      }
    } else if (purchaseDetails.status == PurchaseStatus.purchased ||
        purchaseDetails.status == PurchaseStatus.restored) {
      // Тільки наші premium-продукти (включно з legacy)
      if (!_premiumProductIds.contains(purchaseDetails.productID)) {
        debugPrint('Ignore non-premium product: ${purchaseDetails.productID}');
        return;
      }

      if (purchaseDetails.status == PurchaseStatus.restored) {
        // Restored = магазин вже підтвердив що покупка валідна
        debugPrint('✅ Purchase restored from store: ${purchaseDetails.productID}');
        await _deliverProduct(purchaseDetails);
        onPurchaseSuccess?.call();
      } else {
        // Нова покупка — верифікуємо на сервері
        final isValid = await _verifyPurchaseOnServer(purchaseDetails);
        if (isValid) {
          debugPrint('✅ Purchase verified: ${purchaseDetails.productID}');
          await _deliverProduct(purchaseDetails);
          onPurchaseSuccess?.call();
        } else {
          debugPrint('❌ Purchase verification FAILED: ${purchaseDetails.productID}');
          onPurchaseError?.call('Не вдалося підтвердити покупку');
        }
      }
    } else if (purchaseDetails.status == PurchaseStatus.canceled) {
      debugPrint('Purchase canceled');
      onPurchaseError?.call('Покупку скасовано');
    }

    // Complete the purchase (важливо!)
    if (purchaseDetails.pendingCompletePurchase) {
      await _inAppPurchase.completePurchase(purchaseDetails);
    }
  }

  /// Верифікація покупки на нашому сервері
  /// Сервер перевіряє токен через Google Play Developer API / Apple receipt verification
  Future<bool> _verifyPurchaseOnServer(PurchaseDetails purchaseDetails) async {
    const maxRetries = 4;
    final verificationData = purchaseDetails.verificationData;
    int serverErrorCount = 0;

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
            .timeout(const Duration(seconds: 15));

        if (response.statusCode == 200) {
          final data = json.decode(response.body);
          return data['valid'] == true;
        }

        if (response.statusCode == 503) {
          serverErrorCount++;
        }

        debugPrint(
          '⚠️ Server verification failed: HTTP ${response.statusCode} (attempt $attempt/$maxRetries)',
        );
        if (attempt < maxRetries) {
          await Future.delayed(const Duration(milliseconds: 800));
        }
      } catch (e) {
        serverErrorCount++;
        debugPrint('Verification error: $e (attempt $attempt/$maxRetries)');
        if (attempt < maxRetries) {
          await Future.delayed(const Duration(milliseconds: 800));
        }
      }
    }

    // If ALL failures were server/network errors (503, timeout, etc.),
    // trust StoreKit — Apple already validated the purchase on-device.
    if (serverErrorCount >= maxRetries) {
      debugPrint(
        '⚠️ Server unreachable/misconfigured for all $maxRetries attempts — '
        'trusting StoreKit for ${purchaseDetails.productID}',
      );
      return true;
    }

    onPurchaseError?.call('Не вдалося перевірити покупку. Спробуйте пізніше.');
    return false;
  }

  Future<void> _deliverProduct(PurchaseDetails purchaseDetails) async {
    // Будь-яка покупка активує Premium (прибирає рекламу)
    await _savePremiumStatus(true);

    // Notify AdService to stop showing ads
    AdService().setPremiumStatus(true);

    debugPrint(
      '🎉 Premium activated for product: ${purchaseDetails.productID}',
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

  // Купити Premium
  Future<bool> buyPremium() async {
    if (_isPremium) {
      debugPrint('Already premium — skipping purchase');
      onPurchaseSuccess?.call();
      return true;
    }
    if (products.isEmpty) {
      debugPrint('No products loaded');
      await loadProducts();
    }

    ProductDetails? product;
    try {
      product = products.firstWhere((p) => p.id == _premiumProductId);
    } catch (e) {
      debugPrint(
        'Product $_premiumProductId not found in ${products.map((p) => p.id).toList()}',
      );
      return false;
    }

    final PurchaseParam purchaseParam = PurchaseParam(productDetails: product);

    // Non-consumable - одноразова покупка назавжди
    return _inAppPurchase.buyNonConsumable(purchaseParam: purchaseParam);
  }

  /// Відновити покупки (якщо перевстановив додаток).
  /// Чекає на відповідь з магазину та повертає true, якщо premium активовано.
  Future<bool> restorePurchases() async {
    await _inAppPurchase.restorePurchases();
    // Чекаємо на purchaseStream (до 8 сек) — магазин може відповідати повільно
    for (var i = 0; i < 10; i++) {
      await Future.delayed(const Duration(milliseconds: 800));
      if (_isPremium) return true;
    }
    return _isPremium;
  }

  void dispose() {
    _subscription?.cancel();
    premiumNotifier.dispose();
  }
}
