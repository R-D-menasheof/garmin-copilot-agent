import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:vitalis/services/auth_http_client.dart';

void main() {
  group('AuthHttpClient', () {
    test('injects x-api-key when no bearer token is set', () async {
      String? seenKey;
      final inner = MockClient((req) async {
        seenKey = req.headers['x-api-key'];
        return http.Response('{}', 200);
      });
      final client = AuthHttpClient(inner, apiKey: 'the-key');

      await client.get(Uri.parse('http://t/x'));

      expect(seenKey, 'the-key');
    });

    test('injects Bearer header when a token is set', () async {
      String? auth;
      final inner = MockClient((req) async {
        auth = req.headers['authorization'];
        return http.Response('{}', 200);
      });
      final client = AuthHttpClient(inner, apiKey: 'k')..updateToken('tok-1');

      await client.get(Uri.parse('http://t/x'));

      expect(auth, 'Bearer tok-1');
    });

    test('clearToken reverts to x-api-key', () async {
      final seen = <String?>[];
      final inner = MockClient((req) async {
        seen.add(req.headers['authorization']);
        seen.add(req.headers['x-api-key']);
        return http.Response('{}', 200);
      });
      final client = AuthHttpClient(inner, apiKey: 'k')..updateToken('tok');
      client.clearToken();

      await client.get(Uri.parse('http://t/x'));

      expect(seen[0], isNull); // no Authorization
      expect(seen[1], 'k'); // x-api-key present
    });

    test('on 401 refreshes the token and retries once with the new token', () async {
      final tokens = <String?>[];
      var calls = 0;
      final inner = MockClient((req) async {
        calls++;
        tokens.add(req.headers['authorization']);
        return http.Response('{}', calls == 1 ? 401 : 200);
      });
      final client = AuthHttpClient(inner, apiKey: 'k')..updateToken('old');
      client.setRefresher(() async {
        client.updateToken('new');
        return true;
      });

      final resp = await client.get(Uri.parse('http://t/x'));

      expect(resp.statusCode, 200);
      expect(calls, 2);
      expect(tokens[0], 'Bearer old');
      expect(tokens[1], 'Bearer new');
    });

    test('preserves the POST body across the retry', () async {
      final bodies = <String>[];
      var calls = 0;
      final inner = MockClient((req) async {
        calls++;
        bodies.add(req.body);
        return http.Response('{}', calls == 1 ? 401 : 200);
      });
      final client = AuthHttpClient(inner, apiKey: 'k')..updateToken('old');
      client.setRefresher(() async {
        client.updateToken('new');
        return true;
      });

      await client.post(
        Uri.parse('http://t/x'),
        headers: {'Content-Type': 'application/json'},
        body: '{"a":1}',
      );

      expect(bodies, ['{"a":1}', '{"a":1}']);
    });

    test('without a refresher a 401 is returned without retry', () async {
      var calls = 0;
      final inner = MockClient((req) async {
        calls++;
        return http.Response('{}', 401);
      });
      final client = AuthHttpClient(inner, apiKey: 'k')..updateToken('old');

      final resp = await client.get(Uri.parse('http://t/x'));

      expect(resp.statusCode, 401);
      expect(calls, 1);
    });

    test('concurrent 401s trigger only a single refresh', () async {
      var refreshCount = 0;
      var calls = 0;
      final inner = MockClient((req) async {
        calls++;
        return http.Response('{}', calls <= 2 ? 401 : 200);
      });
      final client = AuthHttpClient(inner, apiKey: 'k')..updateToken('old');
      client.setRefresher(() async {
        refreshCount++;
        await Future<void>.delayed(const Duration(milliseconds: 10));
        client.updateToken('new');
        return true;
      });

      await Future.wait([
        client.get(Uri.parse('http://t/a')),
        client.get(Uri.parse('http://t/b')),
      ]);

      expect(refreshCount, 1);
    });
  });
}
