import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:vitalis/services/api_client.dart';
import 'package:vitalis/models/day_tracking_override.dart';
import 'package:vitalis/models/meal_entry.dart';
import 'package:vitalis/models/nutrition_source.dart';
import 'package:vitalis/models/recommendation_status.dart';

void main() {
  group('ApiClient', () {
    late ApiClient client;

    test('getNutrition parses response correctly', () async {
      final mockClient = MockClient((req) async {
        expect(req.url.path, contains('/v1/nutrition'));
        return http.Response(
          jsonEncode({
            'meals': {
              '2026-04-04': [
                {
                  'food_name': 'banana',
                  'calories': 89,
                  'protein_g': 1.1,
                  'carbs_g': 22.8,
                  'fat_g': 0.3,
                  'source': 'history',
                  'timestamp': '2026-04-04T12:00:00',
                }
              ]
            }
          }),
          200,
        );
      });

      client = ApiClient(
        baseUrl: 'http://test/api',
        apiKey: 'test-key',
        httpClient: mockClient,
      );

      final result = await client.getNutrition(
        DateTime(2026, 4, 4),
        DateTime(2026, 4, 4),
      );

      expect(result['2026-04-04'], isNotNull);
      expect(result['2026-04-04']!.length, 1);
      expect(result['2026-04-04']!.first.foodName, 'banana');
    });

    test('postMeal sends correct body', () async {
      final mockClient = MockClient((req) async {
        final body = jsonDecode(req.body) as Map<String, dynamic>;
        expect(body['food_name'], 'banana');
        expect(body['calories'], 89);
        expect(req.headers['x-api-key'], 'test-key');
        return http.Response(
          jsonEncode({
            'meal': {
              'food_name': 'banana',
              'calories': 89,
              'protein_g': 1.1,
              'carbs_g': 22.8,
              'fat_g': 0.3,
              'source': 'history',
              'timestamp': '2026-04-04T12:00:00',
            }
          }),
          201,
        );
      });

      client = ApiClient(
        baseUrl: 'http://test/api',
        apiKey: 'test-key',
        httpClient: mockClient,
      );

      final meal = MealEntry(
        foodName: 'banana',
        calories: 89,
        proteinG: 1.1,
        carbsG: 22.8,
        fatG: 0.3,
        source: NutritionSource.history,
        timestamp: DateTime(2026, 4, 4, 12, 0),
      );

      final result = await client.postMeal(meal);
      expect(result.foodName, 'banana');
    });

    test('handles network error', () async {
      final mockClient = MockClient((req) async {
        return http.Response('{"error": "Internal Server Error"}', 500);
      });

      client = ApiClient(
        baseUrl: 'http://test/api',
        apiKey: 'test-key',
        httpClient: mockClient,
      );

      expect(
        () => client.getNutrition(DateTime(2026, 4, 4), DateTime(2026, 4, 4)),
        throwsA(isA<ApiException>()),
      );
    });

    test('getBiometrics parses date-keyed records', () async {
      final mockClient = MockClient((req) async {
        expect(req.url.path, contains('/v1/biometrics'));
        expect(req.url.queryParameters['from'], '2026-04-01');
        expect(req.url.queryParameters['to'], '2026-04-03');
        return http.Response(
          jsonEncode({
            'biometrics': {
              '2026-04-01': {
                'date': '2026-04-01',
                'resting_hr': 64,
                'hrv_ms': 28,
                'weight_kg': 112.0,
                'vo2max': 42.5,
              },
              '2026-04-03': {
                'date': '2026-04-03',
                'resting_hr': 62,
                'sleep_seconds': 21600,
              },
            }
          }),
          200,
        );
      });

      client = ApiClient(
        baseUrl: 'http://test/api',
        apiKey: 'test-key',
        httpClient: mockClient,
      );

      final result = await client.getBiometrics(
        DateTime(2026, 4, 1),
        DateTime(2026, 4, 3),
      );

      expect(result, hasLength(2));
      expect(result[DateTime(2026, 4, 1)]!.restingHr, 64);
      expect(result[DateTime(2026, 4, 1)]!.vo2max, 42.5);
      expect(result[DateTime(2026, 4, 3)]!.sleepSeconds, 21600);
    });

    test('getBiometrics returns empty map when no data', () async {
      final mockClient = MockClient((req) async {
        return http.Response(jsonEncode({'biometrics': {}}), 200);
      });

      client = ApiClient(
        baseUrl: 'http://test/api',
        apiKey: 'test-key',
        httpClient: mockClient,
      );

      final result = await client.getBiometrics(
        DateTime(2026, 4, 1),
        DateTime(2026, 4, 3),
      );
      expect(result, isEmpty);
    });

    test('getRecommendationStatuses returns list', () async {
      final mockClient = MockClient((req) async {
        return http.Response(
          jsonEncode({
            'statuses': [
              {'rec_id': 'abc', 'status': 'done', 'updated_at': '2026-04-04T12:00:00'},
            ]
          }),
          200,
          headers: {'content-type': 'application/json; charset=utf-8'},
        );
      });

      client = ApiClient(baseUrl: 'http://test/api', apiKey: 'key', httpClient: mockClient);
      final result = await client.getRecommendationStatuses();
      expect(result, hasLength(1));
      expect(result.first.recId, 'abc');
      expect(result.first.status, RecStatus.done);
    });

    test('postRecommendationStatus sends correct payload', () async {
      final mockClient = MockClient((req) async {
        expect(req.method, 'POST');
        final body = jsonDecode(req.body) as Map<String, dynamic>;
        expect(body['rec_id'], 'abc');
        expect(body['status'], 'done');
        return http.Response(jsonEncode({'status': 'ok'}), 201);
      });

      client = ApiClient(baseUrl: 'http://test/api', apiKey: 'key', httpClient: mockClient);
      await client.postRecommendationStatus('abc', RecStatus.done);
    });

    test('includes api key header', () async {
      final mockClient = MockClient((req) async {
        expect(req.headers['x-api-key'], 'my-secret-key');
        return http.Response(jsonEncode({'meals': {}}), 200);
      });

      client = ApiClient(
        baseUrl: 'http://test/api',
        apiKey: 'my-secret-key',
        httpClient: mockClient,
      );

      await client.getNutrition(DateTime(2026, 4, 4), DateTime(2026, 4, 4));
    });

    test('getDayOverrides returns list', () async {
      final mockClient = MockClient((req) async {
        expect(req.url.path, contains('/v1/nutrition/day-overrides'));
        return http.Response(
          jsonEncode({
            'overrides': [
              {
                'date': '2026-07-01',
                'tracked': false,
                'note': 'נסעתי',
                'updated_at': '2026-07-01T20:00:00',
              },
            ]
          }),
          200,
          headers: {'content-type': 'application/json; charset=utf-8'},
        );
      });

      client = ApiClient(baseUrl: 'http://test/api', apiKey: 'key', httpClient: mockClient);
      final result = await client.getDayOverrides();
      expect(result, hasLength(1));
      expect(result.first.date, DateTime(2026, 7, 1));
      expect(result.first.tracked, false);
    });

    test('postDayOverride sends correct payload', () async {
      final mockClient = MockClient((req) async {
        expect(req.method, 'POST');
        expect(req.url.path, contains('/v1/nutrition/day-override'));
        final body = jsonDecode(req.body) as Map<String, dynamic>;
        expect(body['date'], '2026-07-01');
        expect(body['tracked'], false);
        expect(body['note'], 'נסעתי');
        return http.Response(jsonEncode({'status': 'ok'}), 201);
      });

      client = ApiClient(baseUrl: 'http://test/api', apiKey: 'key', httpClient: mockClient);
      await client.postDayOverride(DateTime(2026, 7, 1), false, note: 'נסעתי');
    });
  });
  group('ApiClient auth', () {
    http.Response meOk(_) => http.Response(
          jsonEncode({
            'user_id': 'u',
            'display_name': '',
            'email': '',
            'onboarded': false,
          }),
          200,
        );

    test('sends x-api-key when no bearer token set', () async {
      final mockClient = MockClient((req) async {
        expect(req.headers['x-api-key'], 'key');
        expect(req.headers.containsKey('Authorization'), isFalse);
        return meOk(req);
      });
      final client =
          ApiClient(baseUrl: 'http://test/api', apiKey: 'key', httpClient: mockClient);
      await client.getMe();
    });

    test('updateToken switches to Authorization Bearer header', () async {
      final mockClient = MockClient((req) async {
        expect(req.headers['Authorization'], 'Bearer jwt-123');
        expect(req.headers.containsKey('x-api-key'), isFalse);
        return meOk(req);
      });
      final client =
          ApiClient(baseUrl: 'http://test/api', apiKey: 'key', httpClient: mockClient);
      client.updateToken('jwt-123');
      await client.getMe();
    });

    test('clearToken reverts to x-api-key', () async {
      final mockClient = MockClient((req) async {
        expect(req.headers['x-api-key'], 'key');
        expect(req.headers.containsKey('Authorization'), isFalse);
        return meOk(req);
      });
      final client =
          ApiClient(baseUrl: 'http://test/api', apiKey: 'key', httpClient: mockClient);
      client.updateToken('jwt-123');
      client.clearToken();
      await client.getMe();
    });

    test('getMe parses identity and onboarding', () async {
      final mockClient = MockClient((req) async {
        expect(req.url.path, contains('/v1/me'));
        return http.Response(
          jsonEncode({
            'user_id': 'oid-1',
            'display_name': 'Roei',
            'email': 'r@x.com',
            'onboarded': true,
          }),
          200,
        );
      });
      final client =
          ApiClient(baseUrl: 'http://test/api', apiKey: 'key', httpClient: mockClient);
      final me = await client.getMe();
      expect(me.userId, 'oid-1');
      expect(me.displayName, 'Roei');
      expect(me.email, 'r@x.com');
      expect(me.onboarded, isTrue);
    });
  });}
