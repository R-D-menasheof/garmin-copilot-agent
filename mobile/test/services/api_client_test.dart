import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:vitalis/services/api_client.dart';
import 'package:vitalis/models/meal_entry.dart';
import 'package:vitalis/models/nutrition_source.dart';

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
  });
}
