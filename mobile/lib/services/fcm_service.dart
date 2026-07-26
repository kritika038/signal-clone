import 'dart:async';
import 'dart:io';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'api_service.dart';

// Background and Terminated state handler (must be top-level function)
@pragma('vm:entry-point')
Future<void> firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  await Firebase.initializeApp();
  print("[FCM] Handling background message: ${message.messageId}");
}

class FCMService {
  static final FCMService _instance = FCMService._internal();
  factory FCMService() => _instance;
  FCMService._internal();

  final FirebaseMessaging _messaging = FirebaseMessaging.instance;
  final FlutterLocalNotificationsPlugin _localNotifications = FlutterLocalNotificationsPlugin();
  final ApiService _apiService = ApiService();
  StreamSubscription<String>? _tokenRefreshSubscription;
  StreamSubscription<RemoteMessage>? _foregroundSubscription;
  StreamSubscription<RemoteMessage>? _openedAppSubscription;

  Function(String conversationId)? onOpenConversation;

  Future<void> initialize({required String jwtToken, Function(String)? onOpenChat}) async {
    _apiService.setJwtToken(jwtToken);
    onOpenConversation = onOpenChat;

    // Set background handler
    FirebaseMessaging.onBackgroundMessage(firebaseMessagingBackgroundHandler);

    // Initialize Local Notifications for Foreground display
    const androidSettings = AndroidInitializationSettings('@mipmap/ic_launcher');
    const iosSettings = DarwinInitializationSettings();
    const initSettings = InitializationSettings(android: androidSettings, iOS: iosSettings);

    await _localNotifications.initialize(
      initSettings,
      onDidReceiveNotificationResponse: (response) {
        if (response.payload != null && onOpenConversation != null) {
          onOpenConversation!(response.payload!);
        }
      },
    );
    const channel = AndroidNotificationChannel(
      'high_importance_channel',
      'High Importance Notifications',
      description: 'Messages and group activity',
      importance: Importance.max,
    );
    await _localNotifications
        .resolvePlatformSpecificImplementation<AndroidFlutterLocalNotificationsPlugin>()
        ?.createNotificationChannel(channel);
    await _messaging.setForegroundNotificationPresentationOptions(
      alert: false,
      badge: true,
      sound: false,
    );

    // 1. Request Permission
    NotificationSettings settings = await _messaging.requestPermission(
      alert: true,
      badge: true,
      sound: true,
      provisional: false,
    );

    if (settings.authorizationStatus == AuthorizationStatus.authorized ||
        settings.authorizationStatus == AuthorizationStatus.provisional) {
      print('[FCM] Notification permission granted.');

      // 2. Generate FCM Token & Register with Backend
      await _registerToken();

      // 3. Listen for Token Refresh
      await _tokenRefreshSubscription?.cancel();
      _tokenRefreshSubscription = _messaging.onTokenRefresh.listen((newToken) async {
        print('[FCM] Token refreshed: $newToken');
        await _registerToken(overrideToken: newToken);
      });

      // 4. Foreground Notification Handler
      await _foregroundSubscription?.cancel();
      _foregroundSubscription = FirebaseMessaging.onMessage.listen((RemoteMessage message) {
        print('[FCM] Received foreground message: ${message.notification?.title}');
        _showForegroundNotification(message);
      });

      // 5. Notification Tap (App in Background)
      await _openedAppSubscription?.cancel();
      _openedAppSubscription = FirebaseMessaging.onMessageOpenedApp.listen((RemoteMessage message) {
        print('[FCM] Notification tapped in background');
        _handleMessageTap(message);
      });

      // 6. Terminated State (App Launched from Notification Tap)
      RemoteMessage? initialMessage = await _messaging.getInitialMessage();
      if (initialMessage != null) {
        print('[FCM] App launched from terminated state via notification tap');
        _handleMessageTap(initialMessage);
      }
    } else {
      print('[FCM] User declined or has not accepted notification permission.');
    }
  }

  Future<void> _registerToken({String? overrideToken}) async {
    String? token = overrideToken ?? await _messaging.getToken();
    if (token != null) {
      final preferences = await SharedPreferences.getInstance();
      String? deviceId = preferences.getString('signal_device_id');
      if (deviceId == null) {
        deviceId = 'mobile-${Platform.operatingSystem}-${DateTime.now().microsecondsSinceEpoch}';
        await preferences.setString('signal_device_id', deviceId);
      }
      String platform = Platform.isIOS ? 'ios' : 'android';

      await _apiService.registerDeviceToken(
        deviceId: deviceId,
        platform: platform,
        fcmToken: token,
      );
    }
  }

  void _showForegroundNotification(RemoteMessage message) {
    RemoteNotification? notification = message.notification;
    AndroidNotification? android = message.notification?.android;

    if (notification != null) {
      String? conversationId = message.data['conversation_id'];
      _localNotifications.show(
        notification.hashCode,
        notification.title,
        notification.body,
        NotificationDetails(
          android: AndroidNotificationDetails(
            'high_importance_channel',
            'High Importance Notifications',
            channelDescription: 'This channel is used for important notifications.',
            importance: Importance.max,
            priority: Priority.high,
            icon: android?.smallIcon ?? '@mipmap/ic_launcher',
          ),
          iOS: const DarwinNotificationDetails(
            presentAlert: true,
            presentBadge: true,
            presentSound: true,
          ),
        ),
        payload: conversationId,
      );
    }
  }

  void _handleMessageTap(RemoteMessage message) {
    String? conversationId = message.data['conversation_id'];
    if (conversationId != null && onOpenConversation != null) {
      onOpenConversation!(conversationId);
    }
  }

  Future<void> dispose() async {
    await _tokenRefreshSubscription?.cancel();
    await _foregroundSubscription?.cancel();
    await _openedAppSubscription?.cancel();
  }
}
