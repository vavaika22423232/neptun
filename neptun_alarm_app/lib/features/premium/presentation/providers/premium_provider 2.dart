import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../services/purchase_service.dart';
import '../../../../services/pro_customization_service.dart';
import '../../../../core/di/service_locator.dart';

const Object _premiumErrorUnset = Object();

class PremiumState {
  final bool isPremium;
  final AppTier tier;
  final bool isLoading;
  final bool isPurchasing;
  final String? error;
  /// Реальна ціна з магазину (наприклад «170,00 ₴»). Null — ще не завантажено.
  final String? productPrice;

  const PremiumState({
    this.isPremium = false,
    this.tier = AppTier.free,
    this.isLoading = true,
    this.isPurchasing = false,
    this.error,
    this.productPrice,
  });

  PremiumState copyWith({
    bool? isPremium,
    AppTier? tier,
    bool? isLoading,
    bool? isPurchasing,
    Object? error = _premiumErrorUnset,
    String? productPrice,
  }) {
    return PremiumState(
      isPremium: isPremium ?? this.isPremium,
      tier: tier ?? this.tier,
      isLoading: isLoading ?? this.isLoading,
      isPurchasing: isPurchasing ?? this.isPurchasing,
      error: identical(error, _premiumErrorUnset) ? this.error : error as String?,
      productPrice: productPrice ?? this.productPrice,
    );
  }

  bool get isPro => tier == AppTier.pro;
}

class PremiumNotifier extends Notifier<PremiumState> {
  bool _listenersAttached = false;

  @override
  PremiumState build() {
    final svc = sl<PurchaseService>();
    if (!_listenersAttached) {
      _listenersAttached = true;
      svc.premiumNotifier.addListener(_onChanged);
      svc.tierNotifier.addListener(_onChanged);
      ref.onDispose(() {
        svc.premiumNotifier.removeListener(_onChanged);
        svc.tierNotifier.removeListener(_onChanged);
        _listenersAttached = false;
      });
    }

    // Читаємо ціну з уже завантажених продуктів (якщо є)
    final price = _priceFromProducts(svc);

    // Якщо продукти ще не завантажені — підвантажуємо у фоні
    if (price == null) {
      Future.microtask(() async {
        await svc.loadProducts();
        final loaded = _priceFromProducts(svc);
        if (loaded != null && ref.mounted) {
          state = state.copyWith(productPrice: loaded);
        }
      });
    }

    return PremiumState(
      isPremium: svc.isPremium,
      tier: svc.tier,
      isLoading: false,
      productPrice: price,
    );
  }

  /// Витягує ціну продукту pro_monthly з ProductDetails (дані магазину).
  String? _priceFromProducts(PurchaseService svc) {
    if (svc.products.isEmpty) return null;
    final matched = svc.products
        .where((p) => p.id == svc.proMonthlyId)
        .toList();
    if (matched.isNotEmpty) return matched.first.price;
    return svc.products.first.price;
  }

  void _onChanged() {
    final svc = sl<PurchaseService>();
    state = state.copyWith(
      isPremium: svc.isPremium,
      tier: svc.tier,
      isPurchasing: svc.isPremium ? false : state.isPurchasing,
    );
  }

  /// Покупка [AppTier.pro] через [PurchaseService.buyTier] (IAP product id — усередині сервісу).
  Future<void> buyTier(AppTier tier) async {
    if (state.isPurchasing) return;
    if (tier == AppTier.free) return;
    final svc = sl<PurchaseService>();
    state = state.copyWith(isPurchasing: true, error: null);

    void clearCb() {
      svc.onPurchaseSuccess = null;
      svc.onPurchaseError = null;
    }
    void finish() {
      clearCb();
      if (ref.mounted) state = state.copyWith(isPurchasing: false);
    }

    svc.onPurchaseSuccess = finish;
    svc.onPurchaseError = (msg) {
      clearCb();
      if (ref.mounted) state = state.copyWith(isPurchasing: false, error: msg);
    };

    try {
      final started = await svc.buyTier(tier);
      if (!started) {
        finish();
        if (ref.mounted) {
          state = state.copyWith(
            error: state.error ??
                'Не вдалося відкрити оплату. Перевірте інтернет або оновіть сторінку магазину.',
          );
        }
      }
    } catch (e) {
      finish();
      if (ref.mounted) state = state.copyWith(error: e.toString());
    }
  }

  /// Legacy alias — відкриває місячну Pro-підписку.
  Future<void> buyPremium() => buyTier(AppTier.pro);

  Future<bool> restorePurchases() async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      final success = await sl<PurchaseService>().restorePurchases();
      if (ref.mounted) {
        state = state.copyWith(
          isPremium: success,
          tier: sl<PurchaseService>().tier,
          isLoading: false,
          error: success
              ? null
              : 'Активних покупок для цього акаунта App Store / Google Play не знайдено.',
        );
      }
      return success;
    } catch (e) {
      if (ref.mounted) state = state.copyWith(error: e.toString(), isLoading: false);
      return false;
    }
  }
}

final premiumProvider = NotifierProvider<PremiumNotifier, PremiumState>(() {
  return PremiumNotifier();
});

final proCustomizationProvider = Provider<ProCustomizationService>((ref) {
  return sl<ProCustomizationService>();
});
