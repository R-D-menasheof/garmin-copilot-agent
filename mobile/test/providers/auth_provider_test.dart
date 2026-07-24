import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/testing.dart';
import 'package:http/http.dart' as http;

import 'package:vitalis/providers/auth_provider.dart';
import 'package:vitalis/services/api_client.dart';
import 'package:vitalis/services/auth_service.dart';

/// Fake AuthService returning scripted results.
class FakeAuthService implements AuthService {
  String? tokenToReturn;
  bool throwOnSignIn = false;
  bool throwOnRestore = false;
  int signOutCalls = 0;
  int restoreCalls = 0;

  // When set, restoreSession returns this instead of [tokenToReturn], letting a
  // test script a genuine end-of-session (null) independently of sign-in.
  String? _restoreOverride;
  bool _useRestoreOverride = false;
  void setRestore(String? token) {
    _restoreOverride = token;
    _useRestoreOverride = true;
  }

  @override
  Future<String?> signIn() async {
    if (throwOnSignIn) throw Exception('sign-in failed');
    return tokenToReturn;
  }

  @override
  Future<String?> restoreSession() async {
    restoreCalls++;
    if (throwOnRestore) throw Exception('offline');
    return _useRestoreOverride ? _restoreOverride : tokenToReturn;
  }

  @override
  Future<void> signOut() async => signOutCalls++;
}

Map<String, dynamic> _me({
  String userId = 'oid-1',
  String displayName = 'Roei',
  String email = '',
  bool onboarded = true,
}) =>
    {
      'user_id': userId,
      'display_name': displayName,
      'email': email,
      'onboarded': onboarded,
    };

ApiClient _clientReturningMe(Map<String, dynamic> me) {
  final mock = MockClient((req) async {
    if (req.url.path.contains('/v1/me')) {
      return http.Response(jsonEncode(me), 200);
    }
    return http.Response('{}', 200);
  });
  return ApiClient(baseUrl: 'http://test/api', apiKey: 'key', httpClient: mock);
}

void main() {
  group('AuthProvider', () {
    test('starts unauthenticated', () {
      final p = AuthProvider(_clientReturningMe({}), FakeAuthService());
      expect(p.isAuthenticated, isFalse);
      expect(p.userId, isNull);
    });

    test('signIn success sets identity and pushes token to ApiClient', () async {
      final api = _clientReturningMe({
        'user_id': 'oid-1',
        'display_name': 'Roei',
        'email': 'r@x.com',
        'onboarded': true,
      });
      final auth = FakeAuthService()..tokenToReturn = 'jwt-abc';
      final p = AuthProvider(api, auth);

      final ok = await p.signIn();

      expect(ok, isTrue);
      expect(p.isAuthenticated, isTrue);
      expect(p.userId, 'oid-1');
      expect(p.displayName, 'Roei');
      expect(p.onboarded, isTrue);
    });

    test('signIn cancelled (null token) stays unauthenticated', () async {
      final auth = FakeAuthService()..tokenToReturn = null;
      final p = AuthProvider(_clientReturningMe({}), auth);

      final ok = await p.signIn();

      expect(ok, isFalse);
      expect(p.isAuthenticated, isFalse);
    });

    test('signIn failure stays unauthenticated', () async {
      final auth = FakeAuthService()..throwOnSignIn = true;
      final p = AuthProvider(_clientReturningMe({}), auth);

      final ok = await p.signIn();

      expect(ok, isFalse);
      expect(p.isAuthenticated, isFalse);
    });

    test('signOut clears state and calls service', () async {
      final api = _clientReturningMe({
        'user_id': 'oid-1',
        'display_name': 'Roei',
        'email': '',
        'onboarded': true,
      });
      final auth = FakeAuthService()..tokenToReturn = 'jwt-abc';
      final p = AuthProvider(api, auth);
      await p.signIn();

      await p.signOut();

      expect(p.isAuthenticated, isFalse);
      expect(p.userId, isNull);
      expect(auth.signOutCalls, 1);
    });

    test('tryRestore returns false when no session', () async {
      final auth = FakeAuthService()..tokenToReturn = null;
      final p = AuthProvider(_clientReturningMe({}), auth);

      final ok = await p.tryRestore();

      expect(ok, isFalse);
      expect(p.isAuthenticated, isFalse);
    });

    test('tryRestore restores identity from stored session', () async {
      final api = _clientReturningMe({
        'user_id': 'oid-9',
        'display_name': 'Dana',
        'email': 'd@x.com',
        'onboarded': false,
      });
      final auth = FakeAuthService()..tokenToReturn = 'jwt-restored';
      final p = AuthProvider(api, auth);

      final ok = await p.tryRestore();

      expect(ok, isTrue);
      expect(p.userId, 'oid-9');
      expect(p.onboarded, isFalse);
    });

    test('setOnboarded updates flag and notifies', () async {
      final api = _clientReturningMe({
        'user_id': 'oid-1',
        'display_name': 'Roei',
        'email': '',
        'onboarded': false,
      });
      final p = AuthProvider(api, FakeAuthService()..tokenToReturn = 'jwt');
      await p.signIn();
      expect(p.onboarded, isFalse);

      p.setOnboarded(true);

      expect(p.onboarded, isTrue);
    });

    test('initializing starts true and clears after tryRestore', () async {
      final p = AuthProvider(
        _clientReturningMe(_me()),
        FakeAuthService()..tokenToReturn = null,
      );
      expect(p.initializing, isTrue);

      await p.tryRestore();

      expect(p.initializing, isFalse);
    });

    test('signIn retries getMe through a transient cold-start failure', () async {
      var meCalls = 0;
      final mock = MockClient((req) async {
        if (req.url.path.contains('/v1/me')) {
          meCalls++;
          if (meCalls == 1) return http.Response('{}', 503);
          return http.Response(jsonEncode(_me()), 200);
        }
        return http.Response('{}', 200);
      });
      final api =
          ApiClient(baseUrl: 'http://test/api', apiKey: 'key', httpClient: mock);
      final p = AuthProvider(
        api,
        FakeAuthService()..tokenToReturn = 'jwt',
        retryBackoff: const Duration(milliseconds: 1),
      );

      final ok = await p.signIn();

      expect(ok, isTrue);
      expect(meCalls, 2);
      expect(p.userId, 'oid-1');
    });

    test('signIn fails (no retry) when getMe returns 401', () async {
      final mock = MockClient((req) async {
        if (req.url.path.contains('/v1/me')) return http.Response('{}', 401);
        return http.Response('{}', 200);
      });
      final api =
          ApiClient(baseUrl: 'http://test/api', apiKey: 'key', httpClient: mock);
      final p = AuthProvider(
        api,
        FakeAuthService()..tokenToReturn = 'jwt',
        retryBackoff: const Duration(milliseconds: 1),
      );

      final ok = await p.signIn();

      expect(ok, isFalse);
      expect(p.isAuthenticated, isFalse);
    });

    test('refreshToken applies a token when a session exists, false otherwise',
        () async {
      final auth = FakeAuthService()..tokenToReturn = 'jwt';
      final p = AuthProvider(_clientReturningMe(_me()), auth);

      expect(await p.refreshToken(), isTrue);

      auth.setRestore(null);
      expect(await p.refreshToken(), isFalse);
    });

    test('a 401 on a request refreshes the token and retries once', () async {
      var timelineCalls = 0;
      final mock = MockClient((req) async {
        if (req.url.path.contains('/v1/me')) {
          return http.Response(jsonEncode(_me()), 200);
        }
        if (req.url.path.contains('/v1/timeline')) {
          timelineCalls++;
          if (timelineCalls == 1) return http.Response('{}', 401);
          return http.Response(jsonEncode({'events': []}), 200);
        }
        return http.Response('{}', 200);
      });
      final api =
          ApiClient(baseUrl: 'http://test/api', apiKey: 'key', httpClient: mock);
      final auth = FakeAuthService()..tokenToReturn = 'jwt';
      final p = AuthProvider(api, auth);
      await p.signIn();

      final events = await api.getTimeline();

      expect(events, isEmpty);
      expect(timelineCalls, 2);
      expect(p.isAuthenticated, isTrue);
    });

    test('an unrecoverable 401 (no session) signs the user out', () async {
      final mock = MockClient((req) async {
        if (req.url.path.contains('/v1/me')) {
          return http.Response(jsonEncode(_me()), 200);
        }
        return http.Response('{}', 401);
      });
      final api =
          ApiClient(baseUrl: 'http://test/api', apiKey: 'key', httpClient: mock);
      final auth = FakeAuthService()..tokenToReturn = 'jwt';
      final p = AuthProvider(api, auth);
      await p.signIn();
      expect(p.isAuthenticated, isTrue);

      auth.setRestore(null); // session genuinely gone
      try {
        await api.getTimeline();
      } catch (_) {}

      expect(p.isAuthenticated, isFalse);
      expect(auth.signOutCalls, greaterThanOrEqualTo(1));
    });

    test('a transient refresh failure on 401 does not sign out', () async {
      final mock = MockClient((req) async {
        if (req.url.path.contains('/v1/me')) {
          return http.Response(jsonEncode(_me()), 200);
        }
        return http.Response('{}', 401);
      });
      final api =
          ApiClient(baseUrl: 'http://test/api', apiKey: 'key', httpClient: mock);
      final auth = FakeAuthService()..tokenToReturn = 'jwt';
      final p = AuthProvider(api, auth);
      await p.signIn();

      auth.throwOnRestore = true; // transient (offline)
      try {
        await api.getTimeline();
      } catch (_) {}

      expect(p.isAuthenticated, isTrue);
      expect(auth.signOutCalls, 0);
    });
  });
}
