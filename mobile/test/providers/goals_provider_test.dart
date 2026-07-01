import 'package:flutter_test/flutter_test.dart';

import 'package:vitalis/providers/goals_provider.dart';
import 'package:vitalis/models/nutrition_goal.dart';
import 'package:vitalis/models/training_program.dart';
import 'package:vitalis/services/api_client.dart';
import 'package:http/testing.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

const _hebrewWeekdays = ['שני', 'שלישי', 'רביעי', 'חמישי', 'שישי', 'שבת', 'ראשון'];

String _todayHebrewName() => _hebrewWeekdays[DateTime.now().weekday - 1];

TrainingProgram _programWithSessionToday(String type) => TrainingProgram(
      id: 'p1',
      name: 'Test Program',
      goal: 'vo2max',
      durationWeeks: 4,
      weeks: [
        TrainingWeek(weekNumber: 1, sessions: [
          TrainingSession(day: _todayHebrewName(), type: type),
        ]),
      ],
      createdAt: DateTime(2026, 1, 1),
    );

Future<GoalsProvider> _providerWithGoal() async {
  final mockClient = MockClient((req) async {
    return http.Response(
      jsonEncode({
        'goal': {
          'date': '2026-04-04',
          'calories_target': 2200,
          'protein_g_target': 180,
          'carbs_g_target': 250,
          'fat_g_target': 70,
          'rest_calories_target': 2600,
          'rest_carbs_g_target': 300,
          'set_by': 'agent',
        }
      }),
      200,
    );
  });
  final client = ApiClient(baseUrl: 'http://test/api', apiKey: 'key', httpClient: mockClient);
  final p = GoalsProvider(client);
  await p.loadGoals();
  return p;
}

void main() {
  group('GoalsProvider', () {
    test('compliancePct calculates correctly', () {
      final mockClient = MockClient((req) async => http.Response('', 404));
      final client = ApiClient(
        baseUrl: 'http://test/api',
        apiKey: 'test-key',
        httpClient: mockClient,
      );

      final provider = GoalsProvider(client);

      // No goal set
      expect(provider.compliancePct(1000), isNull);
    });

    test('compliancePct returns percentage of target', () {
      final mockClient = MockClient((req) async {
        return http.Response(
          jsonEncode({
            'goal': {
              'date': '2026-04-04',
              'calories_target': 2200,
              'protein_g_target': 180,
              'carbs_g_target': 250,
              'fat_g_target': 70,
              'set_by': 'agent',
            }
          }),
          200,
        );
      });

      final client = ApiClient(
        baseUrl: 'http://test/api',
        apiKey: 'test-key',
        httpClient: mockClient,
      );

      final provider = GoalsProvider(client);

      // Manually simulate loaded goal
      provider.loadGoals().then((_) {
        final pct = provider.compliancePct(1100);
        expect(pct, closeTo(50.0, 1.0));
      });
    });

    group('todayCaloriesTarget (training-aware)', () {
      test('uses rest target when TrainingDayService says rest day', () async {
        final provider = await _providerWithGoal();
        final target = provider.todayCaloriesTarget(
          activeProgram: _programWithSessionToday('rest'),
        );

        expect(target, 2600);
      });

      test('uses primary target when TrainingDayService says training day', () async {
        final provider = await _providerWithGoal();
        final target = provider.todayCaloriesTarget(
          activeProgram: _programWithSessionToday('swimming'),
        );

        expect(target, 2200);
      });

      test('falls back to weekend heuristic when no active program', () async {
        final provider = await _providerWithGoal();
        // No active program supplied at all.
        final expectedTarget = NutritionGoal.isRestDay() ? 2600 : 2200;

        expect(provider.todayCaloriesTarget(), expectedTarget);
      });
    });
  });
}
