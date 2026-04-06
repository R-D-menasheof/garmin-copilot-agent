import 'package:flutter/foundation.dart';

import '../models/meal_template.dart';
import '../models/plan_day.dart';
import '../services/api_client.dart';

class PlanProvider extends ChangeNotifier {
  final ApiClient _api;

  PlanDay? _currentPlan;
  bool _loading = false;

  PlanProvider(this._api);

  PlanDay? get currentPlan => _currentPlan;
  bool get loading => _loading;

  Future<void> loadPlanDay(DateTime day) async {
    _loading = true;
    notifyListeners();
    try {
      _currentPlan = await _api.getPlanDay(day);
    } finally {
      _loading = false;
      notifyListeners();
    }
  }

  Future<void> savePlanDay(
    DateTime day, {
    required List<String> templateIds,
    String? notes,
  }) async {
    _loading = true;
    notifyListeners();
    try {
      _currentPlan = await _api.savePlanDay(
        day,
        templateIds: templateIds,
        notes: notes,
      );
    } finally {
      _loading = false;
      notifyListeners();
    }
  }

  List<MealTemplate> plannedTemplates(
    List<MealTemplate> templates, {
    List<String>? templateIds,
  }) {
    final selectedIds = templateIds ?? _currentPlan?.templateIds ?? const <String>[];
    final selectedIdSet = selectedIds.toSet();
    return templates.where((template) => selectedIdSet.contains(template.id)).toList();
  }

  List<String> groceryLines(
    List<MealTemplate> templates, {
    List<String>? templateIds,
  }) {
    final counts = <String, int>{};
    for (final template in plannedTemplates(templates, templateIds: templateIds)) {
      for (final meal in template.meals) {
        counts.update(meal.foodName, (value) => value + 1, ifAbsent: () => 1);
      }
    }

    return counts.entries
        .map((entry) => '${entry.key} x${entry.value}')
        .toList();
  }

  String buildGroceryExport(
    List<MealTemplate> templates, {
    List<String>? templateIds,
  }) {
    final lines = groceryLines(templates, templateIds: templateIds);
    if (lines.isEmpty) {
      return 'אין פריטים ברשימת הקניות';
    }

    return lines.join('\n');
  }
}