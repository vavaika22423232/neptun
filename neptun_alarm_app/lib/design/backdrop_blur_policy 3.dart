import 'package:flutter/foundation.dart'
    show defaultTargetPlatform, kIsWeb, TargetPlatform;

/// Skip [BackdropFilter] on Android: GPU cost is high; solid/frosted fills stay.
bool get neptunSkipBackdropBlur =>
    !kIsWeb && defaultTargetPlatform == TargetPlatform.android;
