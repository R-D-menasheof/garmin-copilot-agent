import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:vitalis/models/meal_entry.dart';
import 'package:vitalis/models/nutrition_source.dart';
import 'package:vitalis/services/frequent_foods.dart';

MealEntry _meal(String name, {int cal = 100}) => MealEntry(
      foodName: name,
      calories: cal,
      proteinG: 10,
      carbsG: 20,
      fatG: 5,
      source: NutritionSource.manual,
      timestamp: DateTime(2026, 4, 18, 12, 0),
    );

void main() {
  group('FrequentFoodsService', () {
    setUp(() {
      SharedPreferences.setMockInitialValues({});
    });

    test('records and retrieves foods', () async {
      final svc = FrequentFoodsService();
      await svc.load();

      await svc.record(_meal('בננה', cal: 89));
      await svc.record(_meal('ביצים', cal: 155));

      expect(svc.topN(5), hasLength(2));
      expect(svc.topN(5).first.foodName, 'בננה');
    });

    test('frequency sorting — most eaten first', () async {
      final svc = FrequentFoodsService();
      await svc.load();

      await svc.record(_meal('בננה'));
      await svc.record(_meal('ביצים'));
      await svc.record(_meal('בננה'));
      await svc.record(_meal('בננה'));

      final top = svc.topN(5);
      expect(top.first.foodName, 'בננה');
      expect(top.first.count, 3);
      expect(top[1].foodName, 'ביצים');
      expect(top[1].count, 1);
    });

    test('search filters by partial name', () async {
      final svc = FrequentFoodsService();
      await svc.load();

      await svc.record(_meal('חומוס'));
      await svc.record(_meal('חומשוקה'));
      await svc.record(_meal('בננה'));

      final results = svc.search('חומ');
      expect(results, hasLength(2));
      expect(results.map((f) => f.foodName), containsAll(['חומוס', 'חומשוקה']));
    });

    test('search is case-insensitive', () async {
      final svc = FrequentFoodsService();
      await svc.load();

      await svc.record(_meal('Banana'));

      expect(svc.search('banana'), hasLength(1));
      expect(svc.search('BANANA'), hasLength(1));
    });

    test('empty search returns empty', () async {
      final svc = FrequentFoodsService();
      await svc.load();

      expect(svc.search(''), isEmpty);
    });

    test('topN respects limit', () async {
      final svc = FrequentFoodsService();
      await svc.load();

      for (int i = 0; i < 10; i++) {
        await svc.record(_meal('food_$i'));
      }

      expect(svc.topN(3), hasLength(3));
      expect(svc.topN(20), hasLength(10));
    });

    test('toMealEntry creates valid entry', () async {
      final svc = FrequentFoodsService();
      await svc.load();

      await svc.record(_meal('בננה', cal: 89));
      final food = svc.topN(1).first;
      final entry = food.toMealEntry();

      expect(entry.foodName, 'בננה');
      expect(entry.calories, 89);
      expect(entry.source, NutritionSource.history);
    });

    test('persists across load cycles', () async {
      final svc1 = FrequentFoodsService();
      await svc1.load();
      await svc1.record(_meal('בננה'));
      await svc1.record(_meal('בננה'));

      // Simulate new instance loading from disk
      final svc2 = FrequentFoodsService();
      await svc2.load();

      expect(svc2.topN(5), hasLength(1));
      expect(svc2.topN(5).first.count, 2);
    });

    test('updates nutrition on re-record', () async {
      final svc = FrequentFoodsService();
      await svc.load();

      await svc.record(_meal('בננה', cal: 89));
      await svc.record(_meal('בננה', cal: 95)); // updated cal

      final food = svc.topN(1).first;
      expect(food.calories, 95); // takes latest
      expect(food.count, 2);
    });
  });
}
