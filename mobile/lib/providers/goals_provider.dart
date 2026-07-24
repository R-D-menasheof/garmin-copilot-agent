import 'package:flutter/foundation.dart';

import '../models/nutrition_goal.dart';
import '../models/training_program.dart';
import '../services/api_client.dart';

/// State management for nutrition goals and compliance tracking.
class GoalsProvider extends ChangeNotifier {
  final ApiClient _api;

  NutritionGoal? _currentGoal;
  NutritionGoal? get currentGoal => _currentGoal;
  bool get isAgentManagedGoal => _currentGoal?.setBy == 'agent';

  bool _loading = false;
  bool get loading => _loading;

  GoalsProvider(this._api);

  Future<void> loadGoals() async {
    _loading = true;
    notifyListeners();
    try {
      _currentGoal = await _api.getGoals();
    } catch (e) {
      // Keep existing goal on error
    } finally {
      _loading = false;
      notifyListeners();
    }
  }

  /// Today's calorie target. Training-schedule aware when [activeProgram]
  /// is supplied (the caller reads this from `TrainingProvider`), otherwise
  /// falls back to the weekend heuristic.
  int todayCaloriesTarget({TrainingProgram? activeProgram}) {
    final goal = _currentGoal;
    if (goal == null) return 2200;
    final isRest = NutritionGoal.isRestDayFor(DateTime.now(), program: activeProgram);
    return (isRest && goal.restCaloriesTarget != null) ? goal.restCaloriesTarget! : goal.caloriesTarget;
  }

  /// Calculate compliance percentage given actual intake.
  double? compliancePct(int actualCalories, {TrainingProgram? activeProgram}) {
    if (_currentGoal == null) {
      return null;
    }
    final target = todayCaloriesTarget(activeProgram: activeProgram);
    if (target == 0) {
      return null;
    }
    return (actualCalories / target * 100)
        .clamp(0, 200)
        .toDouble();
  }
}
