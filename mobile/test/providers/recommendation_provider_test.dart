import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:vitalis/models/recommendation_status.dart';
import 'package:vitalis/providers/recommendation_provider.dart';
import 'package:vitalis/services/api_client.dart';

ApiClient _clientWith(MockClient mock) =>
    ApiClient(baseUrl: 'http://test/api', apiKey: 'key', httpClient: mock);

void main() {
  group('RecommendationProvider', () {
    test('loadStatuses fetches from API', () async {
      final mock = MockClient((req) async {
        return http.Response(
          jsonEncode({
            'statuses': [
              {'rec_id': 'abc', 'status': 'pending', 'updated_at': '2026-04-04T12:00:00'},
            ]
          }),
          200,
          headers: {'content-type': 'application/json; charset=utf-8'},
        );
      });

      final provider = RecommendationProvider(_clientWith(mock));
      await provider.loadStatuses();

      expect(provider.statuses, hasLength(1));
      expect(provider.statuses.first.recId, 'abc');
    });

    test('markDone updates local state and calls API', () async {
      int postCount = 0;
      final mock = MockClient((req) async {
        if (req.method == 'GET') {
          return http.Response(
            jsonEncode({
              'statuses': [
                {'rec_id': 'abc', 'status': 'pending', 'updated_at': '2026-04-04T12:00:00'},
              ]
            }),
            200,
            headers: {'content-type': 'application/json; charset=utf-8'},
          );
        }
        if (req.method == 'POST') {
          postCount++;
          return http.Response(jsonEncode({'status': 'ok'}), 201);
        }
        return http.Response('{}', 404);
      });

      final provider = RecommendationProvider(_clientWith(mock));
      await provider.loadStatuses();
      await provider.markDone('abc');

      expect(provider.getStatus('abc'), RecStatus.done);
      expect(postCount, 1);
    });

    test('markSnoozed updates local state', () async {
      final mock = MockClient((req) async {
        if (req.method == 'GET') {
          return http.Response(
            jsonEncode({
              'statuses': [
                {'rec_id': 'abc', 'status': 'pending', 'updated_at': '2026-04-04T12:00:00'},
              ]
            }),
            200,
            headers: {'content-type': 'application/json; charset=utf-8'},
          );
        }
        return http.Response(jsonEncode({'status': 'ok'}), 201);
      });

      final provider = RecommendationProvider(_clientWith(mock));
      await provider.loadStatuses();
      await provider.markSnoozed('abc');

      expect(provider.getStatus('abc'), RecStatus.snoozed);
    });

    test('markPending undoes done status', () async {
      final mock = MockClient((req) async {
        if (req.method == 'GET') {
          return http.Response(
            jsonEncode({
              'statuses': [
                {'rec_id': 'abc', 'status': 'done', 'updated_at': '2026-04-04T12:00:00'},
              ]
            }),
            200,
            headers: {'content-type': 'application/json; charset=utf-8'},
          );
        }
        return http.Response(jsonEncode({'status': 'ok'}), 201);
      });

      final provider = RecommendationProvider(_clientWith(mock));
      await provider.loadStatuses();
      expect(provider.getStatus('abc'), RecStatus.done);

      await provider.markPending('abc');
      expect(provider.getStatus('abc'), RecStatus.pending);
    });
  });
}
