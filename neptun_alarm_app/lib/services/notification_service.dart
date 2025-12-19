import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:flutter/material.dart';
import 'dart:convert';
import 'package:http/http.dart' as http;

// Background message handler
@pragma('vm:entry-point')
Future<void> firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  debugPrint('Background message: ${message.notification?.title}');
}

class NotificationService {
  static final NotificationService _instance = NotificationService._internal();
  factory NotificationService() => _instance;
  NotificationService._internal();

  final FlutterLocalNotificationsPlugin flutterLocalNotificationsPlugin =
      FlutterLocalNotificationsPlugin();
  final FirebaseMessaging _firebaseMessaging = FirebaseMessaging.instance;

  String? _fcmToken;
  String? get fcmToken => _fcmToken;

  Future<void> initialize() async {
    // Request permission
    NotificationSettings settings = await _firebaseMessaging.requestPermission(
      alert: true,
      badge: true,
      sound: true,
    );

    if (settings.authorizationStatus == AuthorizationStatus.authorized) {
      debugPrint('User granted permission');
    }

    // Initialize local notifications
    const AndroidInitializationSettings initializationSettingsAndroid =
        AndroidInitializationSettings('@mipmap/ic_launcher');

    const DarwinInitializationSettings initializationSettingsIOS =
        DarwinInitializationSettings(
      requestAlertPermission: true,
      requestBadgePermission: true,
      requestSoundPermission: true,
    );

    const InitializationSettings initializationSettings =
        InitializationSettings(
      android: initializationSettingsAndroid,
      iOS: initializationSettingsIOS,
    );

    await flutterLocalNotificationsPlugin.initialize(
      initializationSettings,
      onDidReceiveNotificationResponse: (NotificationResponse response) {
        debugPrint('Notification clicked: ${response.payload}');
      },
    );

    // Create notification channels for Android
    const AndroidNotificationChannel channelCritical = AndroidNotificationChannel(
      'critical_alerts',
      'Критичні тривоги',
      description: 'Сповіщення про ракети та критичні загрози',
      importance: Importance.max,
      playSound: true,
      enableVibration: true,
    );

    const AndroidNotificationChannel channelNormal = AndroidNotificationChannel(
      'normal_alerts',
      'Звичайні тривоги',
      description: 'Сповіщення про дрони',
      importance: Importance.high,
      playSound: true,
    );

    await flutterLocalNotificationsPlugin
        .resolvePlatformSpecificImplementation<
            AndroidFlutterLocalNotificationsPlugin>()
        ?.createNotificationChannel(channelCritical);

    await flutterLocalNotificationsPlugin
        .resolvePlatformSpecificImplementation<
            AndroidFlutterLocalNotificationsPlugin>()
        ?.createNotificationChannel(channelNormal);

    // Get FCM token
    _fcmToken = await _firebaseMessaging.getToken();
    debugPrint('FCM Token: $_fcmToken');

    // Listen to token refresh
    _firebaseMessaging.onTokenRefresh.listen((newToken) {
      _fcmToken = newToken;
      _registerDevice();
    });

    // Handle foreground messages
    FirebaseMessaging.onMessage.listen((RemoteMessage message) {
      _showLocalNotification(message);
    });

    // Handle background messages
    FirebaseMessaging.onBackgroundMessage(firebaseMessagingBackgroundHandler);

    // Handle notification taps when app is in background
    FirebaseMessaging.onMessageOpenedApp.listen((RemoteMessage message) {
      debugPrint('Message clicked: ${message.notification?.title}');
    });

    // Register device with backend
    await _registerDevice();
  }

  Future<void> _showLocalNotification(RemoteMessage message) async {
    final notification = message.notification;
    if (notification == null) return;

    final data = message.data;
    final isCritical = data['type'] == 'rocket' || data['type'] == 'критична';

    final androidDetails = AndroidNotificationDetails(
      isCritical ? 'critical_alerts' : 'normal_alerts',
      isCritical ? 'Критичні тривоги' : 'Звичайні тривоги',
      channelDescription: isCritical
          ? 'Сповіщення про ракети та критичні загрози'
          : 'Сповіщення про дрони',
      importance: isCritical ? Importance.max : Importance.high,
      priority: isCritical ? Priority.max : Priority.high,
      icon: '@mipmap/ic_launcher',
      color: isCritical ? const Color(0xFFE63946) : const Color(0xFFFF9500),
    );

    const iosDetails = DarwinNotificationDetails(
      presentAlert: true,
      presentBadge: true,
      presentSound: true,
    );

    final details = NotificationDetails(
      android: androidDetails,
      iOS: iosDetails,
    );

    await flutterLocalNotificationsPlugin.show(
      notification.hashCode,
      notification.title,
      notification.body,
      details,
      payload: jsonEncode(data),
    );
  }

  Future<void> _registerDevice() async {
    if (_fcmToken == null) return;

    final prefs = await SharedPreferences.getInstance();
    final selectedRegions = prefs.getStringList('selected_regions') ?? [];
    final notificationsEnabled = prefs.getBool('notifications_enabled') ?? true;

    if (!notificationsEnabled || selectedRegions.isEmpty) {
      debugPrint('Notifications disabled or no regions selected');
      return;
    }

    try {
      final response = await http.post(
        Uri.parse('https://neptun.in.ua/api/register-device'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'token': _fcmToken,
          'regions': selectedRegions,
          'device_id': _fcmToken, // Using token as device ID
        }),
      );

      if (response.statusCode == 200) {
        debugPrint('Device registered successfully');
      } else {
        debugPrint('Failed to register device: ${response.statusCode}');
      }
    } catch (e) {
      debugPrint('Error registering device: $e');
    }
  }

  Future<void> updateRegions(List<String> regions) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setStringList('selected_regions', regions);
    await _registerDevice();
  }

  Future<void> setNotificationsEnabled(bool enabled) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('notifications_enabled', enabled);
    if (enabled) {
      await _registerDevice();
    }
  }

  Future<void> sendTestNotification() async {
    // First show local test notification immediately
    await _showTestLocalNotification();
    
    // Then try to send via backend (if Firebase is configured)
    if (_fcmToken == null) {
      debugPrint('No FCM token available');
      return;
    }
    
    try {
      final response = await http.post(
        Uri.parse('https://neptun.in.ua/api/test-notification'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'token': _fcmToken}),
      );

      if (response.statusCode == 200) {
        debugPrint('Test notification sent to backend');
      } else {
        debugPrint('Backend test notification failed: ${response.statusCode}');
      }
    } catch (e) {
      debugPrint('Error sending test notification to backend: $e');
    }
  }

  Future<void> _showTestLocalNotification() async {
    const androidDetails = AndroidNotificationDetails(
      'normal_alerts',
      'Звичайні тривоги',
      channelDescription: 'Сповіщення про дрони',
      importance: Importance.high,
      priority: Priority.high,
      icon: '@mipmap/ic_launcher',
      color: Color(0xFF4A90E2),
    );

    const iosDetails = DarwinNotificationDetails(
      presentAlert: true,
      presentBadge: true,
      presentSound: true,
    );

    const details = NotificationDetails(
      android: androidDetails,
      iOS: iosDetails,
    );

    await flutterLocalNotificationsPlugin.show(
      999, // Test notification ID
      '🧪 Тестове сповіщення',
      'Dron Alerts працює коректно! Ви отримуватимете сповіщення про загрози.',
      details,
      payload: jsonEncode({'type': 'test'}),
    );
  }
}
