import 'package:flutter_test/flutter_test.dart';

import 'package:vitalis/models/nutrition_goal.dart';

void main() {
  test('preserves calorie calculation provenance in JSON', () {
    final goal = NutritionGoal.fromJson({
      'date': '2026-07-24',
      'calories_target': 1800,
      'protein_g_target': 120,
      'carbs_g_target': 195,
      'fat_g_target': 60,
      'set_by': 'agent',
      'calculated_from_weight_kg': 80,
      'estimated_tdee_kcal': 2400,
      'calculation_method': 'mifflin_st_jeor+garmin',
      'calculation_version': 1,
    });

    expect(goal.calculatedFromWeightKg, 80);
    expect(goal.estimatedTdeeKcal, 2400);
    expect(goal.calculationMethod, 'mifflin_st_jeor+garmin');
    expect(goal.calculationVersion, 1);
    expect(goal.toJson()['calculated_from_weight_kg'], 80);
  });
}
