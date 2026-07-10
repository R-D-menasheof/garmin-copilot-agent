import '../models/biometrics_record.dart';
import '../models/meal_entry.dart';

/// A single point on a trend line: (date, value).
typedef TrendPoint = (DateTime, double);

/// Extract per-metric time-series from date-keyed daily biometrics.
///
/// Returns a map of metric key → list of (date, value) sorted ascending
/// (oldest first), with days that have no value for that metric skipped.
/// Every known metric key is present in the result (possibly empty), so
/// callers can look up any key without null-checking.
Map<String, List<TrendPoint>> biometricSeries(
  Map<DateTime, BiometricsRecord> byDate,
) {
  final sortedDates = byDate.keys.toList()..sort();

  final extractors = <String, double? Function(BiometricsRecord)>{
    // Heart / recovery
    'resting_hr': (r) => r.restingHr?.toDouble(),
    'avg_hr': (r) => r.avgHr?.toDouble(),
    'max_hr': (r) => r.maxHr?.toDouble(),
    'hrv_ms': (r) => r.hrvMs?.toDouble(),
    // Sleep (seconds → hours)
    'sleep_hours': (r) => r.sleepSeconds == null ? null : r.sleepSeconds! / 3600.0,
    'deep_sleep_hours': (r) =>
        r.deepSleepSeconds == null ? null : r.deepSleepSeconds! / 3600.0,
    'rem_sleep_hours': (r) =>
        r.remSleepSeconds == null ? null : r.remSleepSeconds! / 3600.0,
    'light_sleep_hours': (r) =>
        r.lightSleepSeconds == null ? null : r.lightSleepSeconds! / 3600.0,
    'sleep_score': (r) => r.sleepScore?.toDouble(),
    // Body
    'weight_kg': (r) => r.weightKg,
    'body_fat_pct': (r) => r.bodyFatPct,
    'bmi': (r) => r.bmi,
    'basal_metabolic_rate': (r) => r.basalMetabolicRate,
    // Fitness
    'vo2max': (r) => r.vo2max,
    // Activity
    'steps': (r) => r.steps?.toDouble(),
    'active_calories': (r) => r.activeCalories?.toDouble(),
    'intensity_minutes': (r) => r.intensityMinutes?.toDouble(),
    'exercise_minutes': (r) => r.exerciseMinutes?.toDouble(),
    'distance_km': (r) =>
        r.distanceMeters == null ? null : r.distanceMeters! / 1000.0,
    'floors_climbed': (r) => r.floorsClimbed?.toDouble(),
    // Vitals
    'spo2_pct': (r) => r.spo2Pct,
    'respiratory_rate': (r) => r.respiratoryRate,
    'body_temp_c': (r) => r.bodyTempC,
    'bp_systolic': (r) => r.bpSystolic?.toDouble(),
  };

  final result = <String, List<TrendPoint>>{};
  for (final entry in extractors.entries) {
    final points = <TrendPoint>[];
    for (final date in sortedDates) {
      final value = entry.value(byDate[date]!);
      if (value != null) points.add((date, value));
    }
    result[entry.key] = points;
  }
  return result;
}

/// Aggregate meals into daily nutrition trend-series.
///
/// Returns keys `calories` and `protein_g`, each a list of (date, total)
/// sorted ascending. Days with no meals are skipped.
Map<String, List<TrendPoint>> nutritionDailySeries(
  Map<DateTime, List<MealEntry>> byDate,
) {
  final sortedDates = byDate.keys.toList()..sort();
  final calories = <TrendPoint>[];
  final protein = <TrendPoint>[];
  for (final date in sortedDates) {
    final meals = byDate[date]!;
    if (meals.isEmpty) continue;
    final totalCal = meals.fold<double>(0, (s, m) => s + m.calories);
    final totalProtein = meals.fold<double>(0, (s, m) => s + m.proteinG);
    calories.add((date, totalCal));
    protein.add((date, totalProtein));
  }
  return {'calories': calories, 'protein_g': protein};
}
