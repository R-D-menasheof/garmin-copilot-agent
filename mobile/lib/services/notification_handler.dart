import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';

/// Which route to open for a notification's data payload. Pure + testable.
/// Returns null when the notification has no associated screen.
String? routeForMessageData(Map<String, dynamic> data) {
  switch (data['type']) {
    case 'report':
      return '/review';
    default:
      return null;
  }
}

/// Wires FCM foreground display (via local notifications) and tap → navigation.
///
/// - Foreground messages are shown as a local notification (Android does not
///   auto-display FCM notifications while the app is open).
/// - Tapping a notification (foreground, background, or cold start) navigates
///   to the relevant screen via [onNavigate].
///
/// Best-effort: platform failures are caught so they never crash the app.
class NotificationHandler {
  final void Function(String route) _onNavigate;
  final FlutterLocalNotificationsPlugin _local;

  NotificationHandler(
    void Function(String route) onNavigate, {
    FlutterLocalNotificationsPlugin? local,
  })  : _onNavigate = onNavigate,
        _local = local ?? FlutterLocalNotificationsPlugin();

  static const AndroidNotificationChannel _channel = AndroidNotificationChannel(
    'vitalis_reports',
    'דוחות בריאות',
    description: 'התראות על דוחות ותובנות בריאות',
    importance: Importance.high,
  );

  Future<void> init() async {
    try {
      await _local.initialize(
        const InitializationSettings(
          android: AndroidInitializationSettings('@mipmap/ic_launcher'),
        ),
        onDidReceiveNotificationResponse: (response) {
          final route = response.payload;
          if (route != null && route.isNotEmpty) _onNavigate(route);
        },
      );
      await _local
          .resolvePlatformSpecificImplementation<
              AndroidFlutterLocalNotificationsPlugin>()
          ?.createNotificationChannel(_channel);

      FirebaseMessaging.onMessage.listen(_showForeground);
      FirebaseMessaging.onMessageOpenedApp.listen((m) => _navigate(m.data));
      final initial = await FirebaseMessaging.instance.getInitialMessage();
      if (initial != null) _navigate(initial.data);
    } catch (e) {
      debugPrint('NotificationHandler init failed: $e');
    }
  }

  void _navigate(Map<String, dynamic> data) {
    final route = routeForMessageData(data);
    if (route != null) _onNavigate(route);
  }

  Future<void> _showForeground(RemoteMessage message) async {
    final notification = message.notification;
    if (notification == null) return;
    final route = routeForMessageData(message.data);
    await _local.show(
      notification.hashCode,
      notification.title,
      notification.body,
      const NotificationDetails(
        android: AndroidNotificationDetails(
          'vitalis_reports',
          'דוחות בריאות',
          channelDescription: 'התראות על דוחות ותובנות בריאות',
          importance: Importance.high,
          priority: Priority.high,
          icon: '@mipmap/ic_launcher',
        ),
      ),
      payload: route,
    );
  }
}
