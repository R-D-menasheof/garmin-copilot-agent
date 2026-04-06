import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:vitalis/models/meal_entry.dart';
import 'package:vitalis/models/meal_template.dart';
import 'package:vitalis/models/nutrition_source.dart';
import 'package:vitalis/providers/plan_provider.dart';
import 'package:vitalis/services/api_client.dart';

void main() {
  group('PlanProvider', () {
    test('loadPlanDay stores plan from the API', () async {
      final mockClient = MockClient((req) async {
        return http.Response(
          jsonEncode({
            'plan': {
              'date': '2026-04-04',
              'template_ids': ['template-1'],
              'notes': 'Training day',
              'created_at': '2026-04-03T20:00:00',
              'updated_at': '2026-04-04T06:00:00',
            }
          }),
          200,
        );
      });

      final provider = PlanProvider(
        ApiClient(
          baseUrl: 'http://test/api',
          apiKey: 'test-key',
          httpClient: mockClient,
        ),
      );

      await provider.loadPlanDay(DateTime(2026, 4, 4));

      expect(provider.currentPlan, isNotNull);
      expect(provider.currentPlan!.templateIds, ['template-1']);
      expect(provider.currentPlan!.notes, 'Training day');
    });

    test('buildGroceryExport aggregates meals from planned templates', () async {
      final mockClient = MockClient((req) async {
        return http.Response(
          jsonEncode({
            'plan': {
              'date': '2026-04-04',
              'template_ids': ['template-1', 'template-2'],
              'notes': 'Training day',
              'created_at': '2026-04-03T20:00:00',
              'updated_at': '2026-04-04T06:00:00',
            }
          }),
          201,
        );
      });

      final provider = PlanProvider(
        ApiClient(
          baseUrl: 'http://test/api',
          apiKey: 'test-key',
          httpClient: mockClient,
        ),
      );

      await provider.savePlanDay(
        DateTime(2026, 4, 4),
        templateIds: ['template-1', 'template-2'],
        notes: 'Training day',
      );

      final export = provider.buildGroceryExport([
        MealTemplate(
          id: 'template-1',
          name: 'Breakfast',
          createdAt: DateTime(2026, 4, 4, 8),
          meals: [
            MealEntry(
              foodName: 'toast',
              calories: 120,
              proteinG: 4,
              carbsG: 20,
              fatG: 2,
              source: NutritionSource.history,
              timestamp: DateTime(2026, 4, 4, 8),
            ),
            MealEntry(
              foodName: 'banana',
              calories: 89,
              proteinG: 1.1,
              carbsG: 22.8,
              fatG: 0.3,
              source: NutritionSource.history,
              timestamp: DateTime(2026, 4, 4, 8, 5),
            ),
          ],
        ),
        MealTemplate(
          id: 'template-2',
          name: 'Snack',
          createdAt: DateTime(2026, 4, 4, 10),
          meals: [
            MealEntry(
              foodName: 'banana',
              calories: 89,
              proteinG: 1.1,
              carbsG: 22.8,
              fatG: 0.3,
              source: NutritionSource.history,
              timestamp: DateTime(2026, 4, 4, 10),
            ),
          ],
        ),
      ]);

      expect(export, contains('banana x2'));
      expect(export, contains('toast x1'));
    });
  });
}