import 'dart:io';
import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';
import '../services/ios_platform_service.dart';

/// iOS-optimized button with haptic feedback
class IOSButton extends StatelessWidget {
  final VoidCallback? onPressed;
  final Widget child;
  final Color? color;
  final Color? disabledColor;
  final EdgeInsetsGeometry? padding;
  final double? minSize;
  final double borderRadius;
  final HapticType hapticType;

  const IOSButton({
    super.key,
    required this.onPressed,
    required this.child,
    this.color,
    this.disabledColor,
    this.padding,
    this.minSize,
    this.borderRadius = 8.0,
    this.hapticType = HapticType.light,
  });

  @override
  Widget build(BuildContext context) {
    if (Platform.isIOS) {
      return CupertinoButton(
        onPressed: onPressed != null
            ? () {
                hapticType.trigger();
                onPressed!();
              }
            : null,
        color: color,
        disabledColor: disabledColor ?? CupertinoColors.systemGrey4,
        padding: padding,
        borderRadius: BorderRadius.circular(borderRadius), minimumSize: Size(minSize ?? kMinInteractiveDimensionCupertino, minSize ?? kMinInteractiveDimensionCupertino),
        child: child,
      );
    }

    return ElevatedButton(
      onPressed: onPressed,
      style: ElevatedButton.styleFrom(
        backgroundColor: color,
        padding: padding,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(borderRadius),
        ),
      ),
      child: child,
    );
  }
}

/// iOS-style action sheet
Future<T?> showIOSActionSheet<T>({
  required BuildContext context,
  required String title,
  String? message,
  required List<IOSActionSheetAction<T>> actions,
  IOSActionSheetAction<T>? cancelAction,
}) async {
  if (Platform.isIOS) {
    // Haptic feedback on show
    HapticType.light.trigger();
    
    return showCupertinoModalPopup<T>(
      context: context,
      builder: (context) => CupertinoActionSheet(
        title: Text(title),
        message: message != null ? Text(message) : null,
        actions: actions
            .map(
              (action) => CupertinoActionSheetAction(
                onPressed: () {
                  HapticType.selection.trigger();
                  Navigator.of(context).pop(action.value);
                },
                isDefaultAction: action.isDefault,
                isDestructiveAction: action.isDestructive,
                child: Text(action.label),
              ),
            )
            .toList(),
        cancelButton: cancelAction != null
            ? CupertinoActionSheetAction(
                onPressed: () {
                  HapticType.light.trigger();
                  Navigator.of(context).pop(cancelAction.value);
                },
                child: Text(cancelAction.label),
              )
            : null,
      ),
    );
  }

  // Fallback to Material bottom sheet on Android
  return showModalBottomSheet<T>(
    context: context,
    builder: (context) => SafeArea(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Padding(
            padding: const EdgeInsets.all(16.0),
            child: Text(
              title,
              style: Theme.of(context).textTheme.titleLarge,
            ),
          ),
          if (message != null)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16.0),
              child: Text(
                message,
                style: Theme.of(context).textTheme.bodyMedium,
              ),
            ),
          const Divider(),
          ...actions.map(
            (action) => ListTile(
              title: Text(
                action.label,
                style: TextStyle(
                  color: action.isDestructive ? Colors.red : null,
                  fontWeight: action.isDefault ? FontWeight.bold : null,
                ),
              ),
              onTap: () => Navigator.of(context).pop(action.value),
            ),
          ),
          if (cancelAction != null) ...[
            const Divider(),
            ListTile(
              title: Text(cancelAction.label),
              onTap: () => Navigator.of(context).pop(cancelAction.value),
            ),
          ],
        ],
      ),
    ),
  );
}

/// Action for iOS action sheet
class IOSActionSheetAction<T> {
  final String label;
  final T value;
  final bool isDefault;
  final bool isDestructive;

  const IOSActionSheetAction({
    required this.label,
    required this.value,
    this.isDefault = false,
    this.isDestructive = false,
  });
}

/// iOS-style alert dialog
Future<bool?> showIOSAlert({
  required BuildContext context,
  required String title,
  String? message,
  String confirmText = 'OK',
  String? cancelText,
  bool isDestructive = false,
}) async {
  if (Platform.isIOS) {
    HapticType.warning.trigger();
    
    return showCupertinoDialog<bool>(
      context: context,
      builder: (context) => CupertinoAlertDialog(
        title: Text(title),
        content: message != null ? Text(message) : null,
        actions: [
          if (cancelText != null)
            CupertinoDialogAction(
              onPressed: () {
                HapticType.light.trigger();
                Navigator.of(context).pop(false);
              },
              child: Text(cancelText),
            ),
          CupertinoDialogAction(
            onPressed: () {
              HapticType.selection.trigger();
              Navigator.of(context).pop(true);
            },
            isDestructiveAction: isDestructive,
            isDefaultAction: !isDestructive,
            child: Text(confirmText),
          ),
        ],
      ),
    );
  }

  return showDialog<bool>(
    context: context,
    builder: (context) => AlertDialog(
      title: Text(title),
      content: message != null ? Text(message) : null,
      actions: [
        if (cancelText != null)
          TextButton(
            onPressed: () => Navigator.of(context).pop(false),
            child: Text(cancelText),
          ),
        TextButton(
          onPressed: () => Navigator.of(context).pop(true),
          style: isDestructive
              ? TextButton.styleFrom(foregroundColor: Colors.red)
              : null,
          child: Text(confirmText),
        ),
      ],
    ),
  );
}

/// iOS-style loading indicator
class IOSLoadingIndicator extends StatelessWidget {
  final double size;
  final Color? color;

  const IOSLoadingIndicator({
    super.key,
    this.size = 20.0,
    this.color,
  });

  @override
  Widget build(BuildContext context) {
    if (Platform.isIOS) {
      return CupertinoActivityIndicator(
        radius: size / 2,
        color: color,
      );
    }

    return SizedBox(
      width: size,
      height: size,
      child: CircularProgressIndicator(
        strokeWidth: 2.0,
        valueColor: color != null ? AlwaysStoppedAnimation(color) : null,
      ),
    );
  }
}

/// iOS-style switch
class IOSSwitch extends StatelessWidget {
  final bool value;
  final ValueChanged<bool>? onChanged;
  final Color? activeColor;

  const IOSSwitch({
    super.key,
    required this.value,
    required this.onChanged,
    this.activeColor,
  });

  @override
  Widget build(BuildContext context) {
    if (Platform.isIOS) {
      return CupertinoSwitch(
        value: value,
        onChanged: onChanged != null
            ? (newValue) {
                HapticType.selection.trigger();
                onChanged!(newValue);
              }
            : null,
        activeTrackColor: activeColor,
      );
    }

    return Switch(
      value: value,
      onChanged: onChanged,
      activeThumbColor: activeColor,
    );
  }
}

/// iOS-style slider
class IOSSlider extends StatelessWidget {
  final double value;
  final double min;
  final double max;
  final int? divisions;
  final ValueChanged<double>? onChanged;
  final Color? activeColor;

  const IOSSlider({
    super.key,
    required this.value,
    this.min = 0.0,
    this.max = 1.0,
    this.divisions,
    required this.onChanged,
    this.activeColor,
  });

  @override
  Widget build(BuildContext context) {
    if (Platform.isIOS) {
      return CupertinoSlider(
        value: value,
        min: min,
        max: max,
        divisions: divisions,
        onChanged: onChanged,
        activeColor: activeColor,
      );
    }

    return Slider(
      value: value,
      min: min,
      max: max,
      divisions: divisions,
      onChanged: onChanged,
      activeColor: activeColor,
    );
  }
}

/// iOS-style pull to refresh
class IOSRefreshIndicator extends StatelessWidget {
  final Widget child;
  final Future<void> Function() onRefresh;

  const IOSRefreshIndicator({
    super.key,
    required this.child,
    required this.onRefresh,
  });

  @override
  Widget build(BuildContext context) {
    if (Platform.isIOS) {
      return CustomScrollView(
        physics: const BouncingScrollPhysics(
          parent: AlwaysScrollableScrollPhysics(),
        ),
        slivers: [
          CupertinoSliverRefreshControl(
            onRefresh: () async {
              HapticType.medium.trigger();
              await onRefresh();
            },
          ),
          SliverToBoxAdapter(child: child),
        ],
      );
    }

    return RefreshIndicator(
      onRefresh: onRefresh,
      child: child,
    );
  }
}

/// iOS-optimized scroll physics
ScrollPhysics get platformScrollPhysics {
  if (Platform.isIOS) {
    return const BouncingScrollPhysics(
      parent: AlwaysScrollableScrollPhysics(),
    );
  }
  return const ClampingScrollPhysics();
}
