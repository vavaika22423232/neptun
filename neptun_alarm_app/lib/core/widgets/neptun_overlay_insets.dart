import 'package:flutter/material.dart';

/// Додатковий нижній відступ для контенту над системним жест-баром / клавіатурою.
double neptunContentBottomPadding(BuildContext context) {
  final mq = MediaQuery.of(context);
  return mq.padding.bottom + mq.viewInsets.bottom;
}
