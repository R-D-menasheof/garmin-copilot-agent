import 'dart:async';

import 'package:firebase_messaging/firebase_messaging.dart';

import 'api_client.dart';

/// Thin abstraction over [FirebaseMessaging] so [PushService] is unit-testable
/// without the Firebase plugin (which needs a device / platform channels).
abstract class PushMessaging {
  /// Ask the OS for notification permission. Returns true if granted.
  Future<bool> requestPermission();

  /// The current FCM registration token for this device (null if unavailable).
  Future<String?> getToken();

  /// Emits a new token whenever FCM rotates it.
  Stream<String> get onTokenRefresh;
}

/// Real [PushMessaging] backed by [FirebaseMessaging].
class FirebasePushMessaging implements PushMessaging {
  final FirebaseMessaging _fm;

  FirebasePushMessaging([FirebaseMessaging? fm])
      : _fm = fm ?? FirebaseMessaging.instance;

  @override
  Future<bool> requestPermission() async {
    final settings = await _fm.requestPermission();
    final status = settings.authorizationStatus;
    return status == AuthorizationStatus.authorized ||
        status == AuthorizationStatus.provisional;
  }

  @override
  Future<String?> getToken() => _fm.getToken();

  @override
  Stream<String> get onTokenRefresh => _fm.onTokenRefresh;
}

/// Registers this device's FCM token with the backend and keeps it fresh.
///
/// Call [register] after sign-in. It is idempotent after the first success and
/// re-registers automatically when FCM rotates the token.
class PushService {
  final PushMessaging _messaging;
  final ApiClient _api;
  StreamSubscription<String>? _sub;
  bool _registered = false;

  PushService(this._messaging, this._api);

  bool get isRegistered => _registered;

  /// Request permission, fetch the FCM token, and register it with the backend.
  Future<void> register() async {
    if (_registered) return;
    final granted = await _messaging.requestPermission();
    if (!granted) return;
    final token = await _messaging.getToken();
    if (token == null || token.isEmpty) return;
    await _api.registerPushToken(token);
    _registered = true;
    _sub ??= _messaging.onTokenRefresh.listen((refreshed) {
      _api.registerPushToken(refreshed).catchError((_) {});
    });
  }

  void dispose() {
    _sub?.cancel();
  }
}
