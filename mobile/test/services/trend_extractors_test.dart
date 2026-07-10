import 'package:flutter_test/flutter_test.dart';
import 'package:vitalis/models/biometrics_record.dart';
import 'package:vitalis/models/meal_entry.dart';
import 'package:vitalis/models/nutrition_source.dart';
import 'package:vitalis/services/trend_extractors.dart';

void main() {
  group('biometricSeries', () {
    test('extracts a metric sorted by date, skipping null days', () {
      final byDate = {
        DateTime(2026, 4, 3): BiometricsRecord(date: DateTime(2026, 4, 3), restingHr: 62),
        DateTime(2026, 4, 1): BiometricsRecord(date: DateTime(2026, 4, 1), restingHr: 64),
        DateTime(2026, 4, 2): BiometricsRecord(date: DateTime(2026, 4, 2)), // null RHR
      };

      final series = biometricSeries(byDate);
      final rhr = series['resting_hr']!;

      expect(rhr, hasLength(2)); // day with null skipped
      expect(rhr.first.$1, DateTime(2026, 4, 1)); // sorted ascending
      expect(rhr.first.$2, 64.0);
      expect(rhr.last.$2, 62.0);
    });

    test('converts sleep seconds to hours', () {
      final byDate = {
        DateTime(2026, 4, 1): BiometricsRecord(
          date: DateTime(2026, 4, 1),
          sleepSeconds: 21600, // 6h
          deepSleepSeconds: 3600, // 1h
        ),
      };
      final series = biometricSeries(byDate);
      expect(series['sleep_hours']!.first.$2, 6.0);
      expect(series['deep_sleep_hours']!.first.$2, 1.0);
    });

    test('converts distance meters to km', () {
      final byDate = {
        DateTime(2026, 4, 1): BiometricsRecord(
          date: DateTime(2026, 4, 1),
          distanceMeters: 5000,
        ),
      };
      expect(biometricSeries(byDate)['distance_km']!.first.$2, 5.0);
    });

    test('extracts vo2max', () {
      final byDate = {
        DateTime(2026, 4, 1): BiometricsRecord(date: DateTime(2026, 4, 1), vo2max: 42.5),
      };
      expect(biometricSeries(byDate)['vo2max']!.first.$2, 42.5);
    });

    test('produces empty lists for a metric with no data', () {
      final byDate = {
        DateTime(2026, 4, 1): BiometricsRecord(date: DateTime(2026, 4, 1), steps: 8000),
      };
      final series = biometricSeries(byDate);
      expect(series['weight_kg'], isEmpty);
      expect(series['steps']!.first.$2, 8000.0);
    });
  });

  group('nutritionDailySeries', () {
    MealEntry meal(double cal, double protein) => MealEntry(
          foodName: 'x',
          calories: cal.toInt(),
          proteinG: protein,
          carbsG: 0,
          fatG: 0,
          source: NutritionSource.history,
          timestamp: DateTime(2026, 4, 1, 12),
        );

    test('sums calories and protein per day', () {
      final byDate = {
        DateTime(2026, 4, 1): [meal(500, 30), meal(300, 20)],
        DateTime(2026, 4, 2): [meal(700, 40)],
      };

      final series = nutritionDailySeries(byDate);
      final cals = series['calories']!;
      expect(cals, hasLength(2));
      expect(cals.first.$1, DateTime(2026, 4, 1));
      expect(cals.first.$2, 800.0);
      expect(series['protein_g']!.first.$2, 50.0);
    });

    test('skips days with no meals', () {
      final byDate = {
        DateTime(2026, 4, 1): <MealEntry>[],
        DateTime(2026, 4, 2): [meal(700, 40)],
      };
      final cals = nutritionDailySeries(byDate)['calories']!;
      expect(cals, hasLength(1));
      expect(cals.first.$2, 700.0);
    });
  });
}
