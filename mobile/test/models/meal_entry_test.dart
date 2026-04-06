import 'package:flutter_test/flutter_test.dart';

import 'package:vitalis/models/meal_entry.dart';
import 'package:vitalis/models/nutrition_source.dart';

void main() {
  group('MealEntry', () {
    test('fromJson round-trip', () {
      final original = MealEntry(
        foodName: 'banana',
        calories: 89,
        proteinG: 1.1,
        carbsG: 22.8,
        fatG: 0.3,
        source: NutritionSource.history,
        timestamp: DateTime(2026, 4, 4, 12, 0),
      );

      final json = original.toJson();
      final restored = MealEntry.fromJson(json);

      expect(restored.foodName, 'banana');
      expect(restored.calories, 89);
      expect(restored.source, NutritionSource.history);
    });

    test('optional fields default to null', () {
      final meal = MealEntry(
        foodName: 'test',
        calories: 100,
        proteinG: 10,
        carbsG: 20,
        fatG: 5,
        source: NutritionSource.manual,
        timestamp: DateTime.now(),
      );

      expect(meal.fiberG, isNull);
      expect(meal.portionDescription, isNull);
    });

    test('copyWith updates synced flag', () {
      final meal = MealEntry(
        foodName: 'test',
        calories: 100,
        proteinG: 10,
        carbsG: 20,
        fatG: 5,
        source: NutritionSource.manual,
        timestamp: DateTime.now(),
        synced: false,
      );

      final synced = meal.copyWith(synced: true);
      expect(synced.synced, true);
      expect(synced.foodName, 'test');
    });
  });

  group('NutritionSource', () {
    test('fromJson handles snake_case', () {
      expect(NutritionSource.fromJson('open_food_facts'),
          NutritionSource.openFoodFacts);
      expect(NutritionSource.fromJson('history'), NutritionSource.history);
    });
  });
}
