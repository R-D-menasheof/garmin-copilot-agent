import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:vitalis/providers/meal_provider.dart';
import 'package:vitalis/services/api_client.dart';
import 'package:vitalis/models/meal_entry.dart';
import 'package:vitalis/models/nutrition_source.dart';

String _dateKey(DateTime day) =>
  '${day.year}-${day.month.toString().padLeft(2, '0')}-${day.day.toString().padLeft(2, '0')}';

void main() {
  setUp(() {
    SharedPreferences.setMockInitialValues({});
  });

  group('MealProvider', () {
    late MealProvider provider;
    late ApiClient client;

    setUp(() {
      final mockClient = MockClient((req) async {
        if (req.method == 'GET') {
          return http.Response(jsonEncode({'meals': {}}), 200);
        }
        if (req.method == 'POST') {
          final body = jsonDecode(req.body);
          return http.Response(jsonEncode({'meal': body}), 201);
        }
        return http.Response('', 404);
      });

      client = ApiClient(
        baseUrl: 'http://test/api',
        apiKey: 'test-key',
        httpClient: mockClient,
      );
      provider = MealProvider(client);
    });

    test('addMeal notifies listeners', () async {
      var notified = false;
      provider.addListener(() => notified = true);

      final meal = MealEntry(
        foodName: 'banana',
        calories: 89,
        proteinG: 1.1,
        carbsG: 22.8,
        fatG: 0.3,
        source: NutritionSource.history,
        timestamp: DateTime.now(),
      );

      await provider.addMeal(meal);
      expect(notified, true);
      expect(provider.todayMeals.length, 1);
    });

    test('loadDay stores meals for the requested date', () async {
      final day = DateTime(2026, 4, 4);
      final mockClient = MockClient((req) async {
        if (req.method == 'GET') {
          return http.Response(
            jsonEncode({
              'meals': {
                _dateKey(day): [
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
        }
        return http.Response('', 404);
      });

      provider = MealProvider(
        ApiClient(
          baseUrl: 'http://test/api',
          apiKey: 'test-key',
          httpClient: mockClient,
        ),
      );

      await provider.loadDay(day);

      expect(provider.mealsForDay(day), hasLength(1));
      expect(provider.mealsForDay(day).single.foodName, 'banana');
    });

    test('loadDay captures an error message on failure', () async {
      final day = DateTime(2026, 4, 5);
      final mockClient = MockClient(
        (_) async => http.Response('{"error":"boom"}', 500),
      );

      provider = MealProvider(
        ApiClient(
          baseUrl: 'http://test/api',
          apiKey: 'test-key',
          httpClient: mockClient,
        ),
      );

      await provider.loadDay(day);

      expect(provider.errorForDay(day), isNotNull);
    });

    test('totalCalories sums meals', () async {
      final meal1 = MealEntry(
        foodName: 'banana',
        calories: 89,
        proteinG: 1.1,
        carbsG: 22.8,
        fatG: 0.3,
        source: NutritionSource.history,
        timestamp: DateTime.now(),
      );
      final meal2 = MealEntry(
        foodName: 'apple',
        calories: 52,
        proteinG: 0.3,
        carbsG: 14,
        fatG: 0.2,
        source: NutritionSource.manual,
        timestamp: DateTime.now(),
      );

      await provider.addMeal(meal1);
      await provider.addMeal(meal2);

      expect(provider.totalCalories, 141);
      expect(provider.totalProtein, closeTo(1.4, 0.01));
    });
  });
}
