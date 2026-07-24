import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:vitalis/providers/profile_provider.dart';
import 'package:vitalis/services/api_client.dart';

ApiClient _client(MockClient mock) =>
    ApiClient(baseUrl: 'http://test/api', apiKey: 'k', httpClient: mock);

void main() {
  group('ProfileProvider', () {
    test('load populates the profile', () async {
      final provider = ProfileProvider(_client(MockClient((req) async {
        expect(req.url.path, endsWith('/v1/profile'));
        return http.Response(
          jsonEncode({
            'profile': {'display_name': 'רועי', 'height_cm': 183.0}
          }),
          200,
          headers: {'content-type': 'application/json; charset=utf-8'},
        );
      })));

      await provider.load();

      expect(provider.profile?.displayName, 'רועי');
      expect(provider.profile?.heightCm, 183.0);
      expect(provider.loading, false);
      expect(provider.error, isNull);
    });

    test('load sets error on failure', () async {
      final provider = ProfileProvider(_client(
        MockClient((req) async => http.Response('{"error":"x"}', 500)),
      ));

      await provider.load();

      expect(provider.profile, isNull);
      expect(provider.error, isNotNull);
    });

    test('save sends only the given changes and updates the profile', () async {
      late Map<String, dynamic> sent;
      final provider = ProfileProvider(_client(MockClient((req) async {
        expect(req.method, 'PATCH');
        sent = jsonDecode(req.body) as Map<String, dynamic>;
        return http.Response(
          jsonEncode({
            'profile': {'display_name': 'רועי חדש'}
          }),
          200,
          headers: {'content-type': 'application/json; charset=utf-8'},
        );
      })));

      final ok = await provider.save({'display_name': 'רועי חדש'});

      expect(ok, true);
      expect(sent['display_name'], 'רועי חדש');
      expect(provider.profile?.displayName, 'רועי חדש');
      expect(provider.saving, false);
    });

    test('save returns false and sets error on failure', () async {
      final provider = ProfileProvider(_client(
        MockClient((req) async => http.Response('{"error":"x"}', 400)),
      ));

      final ok = await provider.save({'display_name': 'x'});

      expect(ok, false);
      expect(provider.error, isNotNull);
    });
  });
}
