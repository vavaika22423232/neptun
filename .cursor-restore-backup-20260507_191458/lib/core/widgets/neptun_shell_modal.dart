import 'dart:ui' show ImageFilter, Offset;

import 'package:flutter/cupertino.dart' as cupertino;
import 'package:flutter/material.dart' hide showDialog;
import 'package:flutter/material.dart' as material_dialog show showDialog;

/// Модалки з маршрутів під [AppShell]: вкладений [Navigator] малює overlay **під**
/// плаваючим HUD. Без [useRootNavigator] шити й діалоги ховаються під шапкою.
///
/// Дефолт [useRootNavigator] = true — як у цих хелперах (у т.ч. Cupertino).
abstract final class NeptunShellModal {
  NeptunShellModal._();

  static Future<T?> showBottomSheet<T>({
    required BuildContext context,
    required WidgetBuilder builder,
    bool useRootNavigator = true,
    bool isScrollControlled = false,
    bool isDismissible = true,
    bool enableDrag = true,
    Color? backgroundColor,
    ShapeBorder? shape,
  }) {
    return showModalBottomSheet<T>(
      context: context,
      useRootNavigator: useRootNavigator,
      isScrollControlled: isScrollControlled,
      isDismissible: isDismissible,
      enableDrag: enableDrag,
      backgroundColor: backgroundColor,
      shape: shape,
      builder: builder,
    );
  }

  static Future<T?> showDialog<T>({
    required BuildContext context,
    required WidgetBuilder builder,
    bool barrierDismissible = true,
    bool useRootNavigator = true,
    Color? barrierColor,
  }) {
    return material_dialog.showDialog<T>(
      context: context,
      useRootNavigator: useRootNavigator,
      barrierDismissible: barrierDismissible,
      barrierColor: barrierColor,
      builder: builder,
    );
  }

  /// iOS action sheet / modal popup — той самий стек, що й [showBottomSheet].
  static Future<T?> showCupertinoModalPopup<T>({
    required BuildContext context,
    required WidgetBuilder builder,
    ImageFilter? filter,
    Color barrierColor = cupertino.kCupertinoModalBarrierColor,
    bool barrierDismissible = true,
    bool useRootNavigator = true,
    bool semanticsDismissible = false,
    RouteSettings? routeSettings,
    Offset? anchorPoint,
    bool? requestFocus,
  }) {
    return cupertino.showCupertinoModalPopup<T>(
      context: context,
      builder: builder,
      filter: filter,
      barrierColor: barrierColor,
      barrierDismissible: barrierDismissible,
      useRootNavigator: useRootNavigator,
      semanticsDismissible: semanticsDismissible,
      routeSettings: routeSettings,
      anchorPoint: anchorPoint,
      requestFocus: requestFocus,
    );
  }

  /// iOS alert — той самий стек, що й [showDialog].
  static Future<T?> showCupertinoDialog<T>({
    required BuildContext context,
    required WidgetBuilder builder,
    String? barrierLabel,
    Color? barrierColor,
    bool useRootNavigator = true,
    bool barrierDismissible = false,
    RouteSettings? routeSettings,
    Offset? anchorPoint,
    bool? requestFocus,
  }) {
    return cupertino.showCupertinoDialog<T>(
      context: context,
      builder: builder,
      barrierLabel: barrierLabel,
      barrierColor: barrierColor,
      useRootNavigator: useRootNavigator,
      barrierDismissible: barrierDismissible,
      routeSettings: routeSettings,
      anchorPoint: anchorPoint,
      requestFocus: requestFocus,
    );
  }
}
