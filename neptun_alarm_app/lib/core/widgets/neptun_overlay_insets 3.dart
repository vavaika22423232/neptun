import 'package:flutter/foundation.dart' show defaultTargetPlatform, kIsWeb;
import 'package:flutter/material.dart';

/// Верхній системний відступ для хрома: [MediaQuery.viewPadding] (не «з’їдається»
/// дочірніми віджетами) + невеликий запас під **Dynamic Island** на iPhone.
double neptunSafeTopInset(BuildContext context) {
  final v = MediaQuery.viewPaddingOf(context).top;
  final islandClass = !kIsWeb &&
      defaultTargetPlatform == TargetPlatform.iOS &&
      v >= 50;
  return v + (islandClass ? 10.0 : 0.0);
}

/// Відступи під прикріплений HUD зверху та таббар знизу ([AppShell]).
class NeptunOverlayInsets extends InheritedWidget {
  const NeptunOverlayInsets({
    super.key,
    required this.contentTop,
    required this.contentBottom,
    required super.child,
  });

  /// Відступ зверху для скрол-контенту (нижче HUD + невеликий зазор).
  final double contentTop;

  /// Відступ знизу для **внутрішнього** padding скролу (кінець списків).
  ///
  /// У [AppShell] таббар і банер стоять у [Column] **під** областю табів, тому
  /// тут **не** додається висота навбару чи реклами — лише невеликий «віддих».
  /// Safe area знизу обробляє [TacticalNavBar].
  ///
  /// Не дублюйте [NeptunSpacing.xxxl] поверх [neptunContentBottomPadding] у тих
  /// самих скролах — значення вже достатнє для кінця списку.
  final double contentBottom;

  static NeptunOverlayInsets? maybeOf(BuildContext context) {
    return context.dependOnInheritedWidgetOfExactType<NeptunOverlayInsets>();
  }

  @override
  bool updateShouldNotify(NeptunOverlayInsets old) =>
      old.contentTop != contentTop || old.contentBottom != contentBottom;
}

/// Константи розмірів «хрома» shell (синхронно з [_NeptunFloatingHud] у app_shell).
abstract final class NeptunShellChrome {
  NeptunShellChrome._();

  /// Висота рядка Telegram всередині капсули (як [_NeptunAppBar.telegramSublineHeight]).
  static const double telegramSublineHeight = 30;

  /// Внутрішня висота HUD без [MediaQuery.viewPadding.top] (ряд 54 + розділювач + блок Telegram у [_NeptunAppBar]).
  static const double hudCardBodyHeight =
      54 + 1 + telegramSublineHeight;

  static const double hudTopMargin = 0;
  static const double contentGapBelowHud = 20;
  /// Синхронно з [TacticalNavBar] `floating: false` (padding + ряд без safe area).
  static const double dockedNavBarHeight = 85;
}

/// Верхній відступ для скрол-контенту (fallback поза [AppShell] — тести, превʼю).
double neptunContentTopPadding(BuildContext context) {
  final o = NeptunOverlayInsets.maybeOf(context)?.contentTop;
  if (o != null) return o;
  final viewTop = MediaQuery.viewPaddingOf(context).top;
  return viewTop +
      NeptunShellChrome.hudTopMargin +
      NeptunShellChrome.hudCardBodyHeight +
      NeptunShellChrome.contentGapBelowHud;
}

/// Нижній відступ (fallback без реклами).
double neptunContentBottomPadding(BuildContext context) {
  final o = NeptunOverlayInsets.maybeOf(context)?.contentBottom;
  if (o != null) return o;
  final b = MediaQuery.viewPaddingOf(context).bottom;
  return b + NeptunShellChrome.dockedNavBarHeight;
}

/// Під капсулою HUD для внутрішніх шапок табів (наприклад чат).
double neptunTightTopUnderHud(BuildContext context) {
  final top = neptunContentTopPadding(context);
  final viewTop = MediaQuery.viewPaddingOf(context).top;
  return (top - 8).clamp(viewTop + 4, double.infinity);
}
