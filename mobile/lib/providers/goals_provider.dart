import 'package:flutter/foundation.dart';

import '../models/nutrition_goal.dart';
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

  /// Calculate compliance percentage given actual intake.
  double? compliancePct(int actualCalories) {
    if (_currentGoal == null || _currentGoal!.caloriesTarget == 0) {
      return null;
    }
    return (actualCalories / _currentGoal!.caloriesTarget * 100)
        .clamp(0, 200)
        .toDouble();
  }
}
