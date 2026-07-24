import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:vitalis/services/api_client.dart';
import 'package:vitalis/services/push_service.dart';

class _FakeMessaging implements PushMessaging {
  bool granted;
  String? token;
  final _ctrl = StreamController<String>.broadcast();

  _FakeMessaging({this.granted = true, this.token = 'fcm-token'});

  @override
  Future<bool> requestPermission() async => granted;

  @override
  Future<String?> getToken() async => token;

  @override
  Stream<String> get onTokenRefresh => _ctrl.stream;
}

ApiClient _countingApi(void Function() onRegister) => ApiClient(
      baseUrl: 'http://test/api',
      apiKey: 'k',
      httpClient: MockClient((req) async {
        if (req.url.path.endsWith('/v1/push/register')) onRegister();
        return http.Response('{"status":"ok"}', 201);
      }),
    );

void main() {
  group('PushService', () {
    test('register posts the token when permission is granted', () async {
      var registered = 0;
      final svc = PushService(
        _FakeMessaging(token: 'fcm-token'),
        _countingApi(() => registered++),
      );

      await svc.register();

      expect(registered, 1);
      expect(svc.isRegistered, true);
    });

    test('register does nothing when permission is denied', () async {
      var registered = 0;
      final svc = PushService(
        _FakeMessaging(granted: false),
        _countingApi(() => registered++),
      );

      await svc.register();

      expect(registered, 0);
      expect(svc.isRegistered, false);
    });

    test('register is idempotent after the first success', () async {
      var registered = 0;
      final svc = PushService(
        _FakeMessaging(token: 'fcm-token'),
        _countingApi(() => registered++),
      );

      await svc.register();
      await svc.register();

      expect(registered, 1);
    });

    test('register skips when token is null', () async {
      var registered = 0;
      final svc = PushService(
        _FakeMessaging(token: null),
        _countingApi(() => registered++),
      );

      await svc.register();

      expect(registered, 0);
      expect(svc.isRegistered, false);
    });
  });
}
