import 'dart:convert';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:vitalis/providers/meal_provider.dart';
import 'package:vitalis/services/api_client.dart';
import 'package:vitalis/models/meal_entry.dart';
import 'package:vitalis/models/nutrition_goal.dart';
import 'package:vitalis/models/nutrition_source.dart';

String _dateKey(DateTime day) =>
  '${day.year}-${day.month.toString().padLeft(2, '0')}-${day.day.toString().padLeft(2, '0')}';

Map<String, dynamic> _mealJson(String name, int calories, DateTime timestamp) => {
      'food_name': name,
      'calories': calories,
      'protein_g': 1.0,
      'carbs_g': 1.0,
      'fat_g': 1.0,
      'source': 'history',
      'timestamp': timestamp.toIso8601String(),
    };

NutritionGoal _buildGoal() => NutritionGoal(
      date: DateTime.now(),
      caloriesTarget: 2000,
      proteinGTarget: 150,
      carbsGTarget: 200,
      fatGTarget: 70,
      setBy: 'agent',
    );

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

  group('MealProvider - Weekly Balance & Day Tracking', () {
    late MealProvider provider;

    test('rollingWeekBalance excludes untracked days from sum', () async {
      final today = DateTime.now();
      final day0 = DateTime(today.year, today.month, today.day);
      final day1 = day0.subtract(const Duration(days: 1));

      final mealsByDate = {
        _dateKey(day0): [_mealJson('food', 2200, day0)], // +200 over target
        _dateKey(day1): [_mealJson('food', 1800, day1)], // -200 under target
        // remaining 5 days of the window: no meals -> auto-untracked, excluded
      };

      final mockClient = MockClient((req) async {
        if (req.url.path.contains('/v1/nutrition/day-overrides')) {
          return http.Response(jsonEncode({'overrides': []}), 200);
        }
        return http.Response(jsonEncode({'meals': mealsByDate}), 200);
      });

      provider = MealProvider(
        ApiClient(baseUrl: 'http://test/api', apiKey: 'key', httpClient: mockClient),
      );

      for (var i = 0; i < 7; i++) {
        await provider.loadDay(day0.subtract(Duration(days: i)));
      }
      await provider.loadDayOverrides();

      expect(provider.rollingWeekBalance(_buildGoal()), 0);
    });

    test('rollingWeekBalance counts tracked days out of 7', () async {
      final today = DateTime.now();
      final day0 = DateTime(today.year, today.month, today.day);

      final mealsByDate = {
        for (var i = 0; i < 3; i++)
          _dateKey(day0.subtract(Duration(days: i))): [
            _mealJson('food', 1900, day0.subtract(Duration(days: i))),
          ],
        // days 3-6: no meals -> untracked
      };

      final mockClient = MockClient((req) async {
        if (req.url.path.contains('/v1/nutrition/day-overrides')) {
          return http.Response(jsonEncode({'overrides': []}), 200);
        }
        return http.Response(jsonEncode({'meals': mealsByDate}), 200);
      });

      provider = MealProvider(
        ApiClient(baseUrl: 'http://test/api', apiKey: 'key', httpClient: mockClient),
      );

      for (var i = 0; i < 7; i++) {
        await provider.loadDay(day0.subtract(Duration(days: i)));
      }
      await provider.loadDayOverrides();

      expect(provider.rollingWeekTrackedCount(), 3);
    });

    test('rollingWeekBalance returns null when no goal is set', () async {
      final mockClient = MockClient((req) async {
        if (req.url.path.contains('/v1/nutrition/day-overrides')) {
          return http.Response(jsonEncode({'overrides': []}), 200);
        }
        return http.Response(jsonEncode({'meals': {}}), 200);
      });

      provider = MealProvider(
        ApiClient(baseUrl: 'http://test/api', apiKey: 'key', httpClient: mockClient),
      );

      expect(provider.rollingWeekBalance(null), isNull);
    });

    test('hasManualOverride is false when no override was ever set, regardless of meals', () async {
      final day = DateTime(2026, 6, 20);
      final mockClient = MockClient((req) async {
        if (req.url.path.contains('/v1/nutrition/day-overrides')) {
          return http.Response(jsonEncode({'overrides': []}), 200);
        }
        return http.Response(jsonEncode({'meals': {}}), 200);
      });

      provider = MealProvider(
        ApiClient(baseUrl: 'http://test/api', apiKey: 'key', httpClient: mockClient),
      );

      await provider.loadDay(day);
      await provider.loadDayOverrides();

      expect(provider.hasManualOverride(day), false);
    });

    test('hasManualOverride is true once an override exists for that day', () async {
      final day = DateTime(2026, 6, 20);
      final mockClient = MockClient((req) async {
        if (req.url.path.contains('/v1/nutrition/day-overrides')) {
          return http.Response(
            jsonEncode({
              'overrides': [
                {
                  'date': _dateKey(day),
                  'tracked': false,
                  'note': '',
                  'updated_at': '2026-06-20T20:00:00',
                },
              ]
            }),
            200,
          );
        }
        return http.Response(jsonEncode({'meals': {}}), 200);
      });

      provider = MealProvider(
        ApiClient(baseUrl: 'http://test/api', apiKey: 'key', httpClient: mockClient),
      );

      await provider.loadDay(day);
      await provider.loadDayOverrides();

      expect(provider.hasManualOverride(day), true);
    });

    test('isDayTracked returns false for days with no meals AND no override', () async {
      final day = DateTime(2026, 6, 20);
      final mockClient = MockClient((req) async {
        if (req.url.path.contains('/v1/nutrition/day-overrides')) {
          return http.Response(jsonEncode({'overrides': []}), 200);
        }
        return http.Response(jsonEncode({'meals': {}}), 200);
      });

      provider = MealProvider(
        ApiClient(baseUrl: 'http://test/api', apiKey: 'key', httpClient: mockClient),
      );

      await provider.loadDay(day);
      await provider.loadDayOverrides();

      expect(provider.isDayTracked(day), false);
    });

    test('isDayTracked returns false when manually overridden untracked', () async {
      final day = DateTime(2026, 6, 20);
      final mockClient = MockClient((req) async {
        if (req.url.path.contains('/v1/nutrition/day-overrides')) {
          return http.Response(
            jsonEncode({
              'overrides': [
                {
                  'date': _dateKey(day),
                  'tracked': false,
                  'note': '',
                  'updated_at': '2026-06-20T20:00:00',
                },
              ]
            }),
            200,
          );
        }
        return http.Response(
          jsonEncode({
            'meals': {
              _dateKey(day): [_mealJson('food', 1900, day)],
            }
          }),
          200,
        );
      });

      provider = MealProvider(
        ApiClient(baseUrl: 'http://test/api', apiKey: 'key', httpClient: mockClient),
      );

      await provider.loadDay(day);
      await provider.loadDayOverrides();

      expect(provider.isDayTracked(day), false);
    });

    test('toggleDayOverride flips tracked state and persists via API', () async {
      final day = DateTime(2026, 6, 20);
      var lastPostBody = <String, dynamic>{};

      final mockClient = MockClient((req) async {
        if (req.url.path.contains('/v1/nutrition/day-overrides')) {
          return http.Response(jsonEncode({'overrides': []}), 200);
        }
        if (req.method == 'POST' && req.url.path.contains('/v1/nutrition/day-override')) {
          lastPostBody = jsonDecode(req.body) as Map<String, dynamic>;
          return http.Response(jsonEncode({'status': 'ok'}), 201);
        }
        if (req.url.path.contains('/v1/nutrition')) {
          return http.Response(
            jsonEncode({
              'meals': {
                _dateKey(day): [_mealJson('food', 500, day)],
              }
            }),
            200,
          );
        }
        return http.Response('', 404);
      });

      provider = MealProvider(
        ApiClient(baseUrl: 'http://test/api', apiKey: 'key', httpClient: mockClient),
      );

      await provider.loadDay(day);
      await provider.loadDayOverrides();

      expect(provider.isDayTracked(day), true); // has meals, no override

      await provider.toggleDayOverride(day);
      expect(provider.isDayTracked(day), false);
      expect(lastPostBody['tracked'], false);

      await provider.toggleDayOverride(day);
      expect(provider.isDayTracked(day), true);
      expect(lastPostBody['tracked'], true);
    });

    test('statusForDay returns correct status for tracked/exceeded/untracked/future days', () async {
      final today = DateTime(DateTime.now().year, DateTime.now().month, DateTime.now().day);
      final trackedOk = today.subtract(const Duration(days: 1));
      final trackedExceeded = today.subtract(const Duration(days: 2));
      final untracked = today.subtract(const Duration(days: 3));
      final future = today.add(const Duration(days: 1));

      final mealsByDate = {
        _dateKey(trackedOk): [_mealJson('food', 1500, trackedOk)],
        _dateKey(trackedExceeded): [_mealJson('food', 2600, trackedExceeded)],
      };

      final mockClient = MockClient((req) async {
        if (req.url.path.contains('/v1/nutrition/day-overrides')) {
          return http.Response(jsonEncode({'overrides': []}), 200);
        }
        return http.Response(jsonEncode({'meals': mealsByDate}), 200);
      });

      provider = MealProvider(
        ApiClient(baseUrl: 'http://test/api', apiKey: 'key', httpClient: mockClient),
      );

      for (final day in [trackedOk, trackedExceeded, untracked, future]) {
        await provider.loadDay(day);
      }
      await provider.loadDayOverrides();

      final goal = _buildGoal();

      expect(provider.statusForDay(trackedOk, goal), DayStatus.trackedWithinBudget);
      expect(provider.statusForDay(trackedExceeded, goal), DayStatus.trackedExceeded);
      expect(provider.statusForDay(untracked, goal), DayStatus.untracked);
      expect(provider.statusForDay(future, goal), DayStatus.future);
    });

    test('loadRange loads meals for all days in range in one call', () async {
      final start = DateTime(2026, 6, 1);
      final end = DateTime(2026, 6, 3);
      var requestCount = 0;

      final mockClient = MockClient((req) async {
        if (req.url.path.contains('/v1/nutrition/day-overrides')) {
          return http.Response(jsonEncode({'overrides': []}), 200);
        }
        requestCount++;
        return http.Response(
          jsonEncode({
            'meals': {
              _dateKey(DateTime(2026, 6, 1)): [_mealJson('a', 100, DateTime(2026, 6, 1))],
              _dateKey(DateTime(2026, 6, 2)): [_mealJson('b', 200, DateTime(2026, 6, 2))],
              _dateKey(DateTime(2026, 6, 3)): [_mealJson('c', 300, DateTime(2026, 6, 3))],
            }
          }),
          200,
        );
      });

      provider = MealProvider(
        ApiClient(baseUrl: 'http://test/api', apiKey: 'key', httpClient: mockClient),
      );

      await provider.loadRange(start, end);

      expect(requestCount, 1);
      expect(provider.mealsForDay(DateTime(2026, 6, 1)), hasLength(1));
      expect(provider.mealsForDay(DateTime(2026, 6, 2)), hasLength(1));
      expect(provider.mealsForDay(DateTime(2026, 6, 3)), hasLength(1));
    });
  });
}
