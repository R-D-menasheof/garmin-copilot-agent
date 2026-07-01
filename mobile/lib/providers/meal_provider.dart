import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter/foundation.dart';

import '../models/day_tracking_override.dart';
import '../models/meal_entry.dart';
import '../models/nutrition_goal.dart';
import '../services/api_client.dart';
import '../services/frequent_foods.dart';

/// Status of a single day for weekly balance / calendar display purposes.
enum DayStatus { trackedWithinBudget, trackedExceeded, untracked, future }

/// State management for meal logging and daily totals.
class MealProvider extends ChangeNotifier {
  final ApiClient _api;
  final FrequentFoodsService _frequentFoods = FrequentFoodsService();

  final Map<String, List<MealEntry>> _mealsByDay = <String, List<MealEntry>>{};
  final Set<String> _loadingDays = <String>{};
  final Map<String, String?> _errorsByDay = <String, String?>{};
  final Map<String, DayTrackingOverride> _overridesByDay = <String, DayTrackingOverride>{};
  List<MealEntry> _recentMeals = <MealEntry>[];

  FrequentFoodsService get frequentFoods => _frequentFoods;

  List<MealEntry> get todayMeals => mealsForDay(DateTime.now());
  List<MealEntry> get recentMeals => List.unmodifiable(_recentMeals);
  bool get loading => isLoadingDay(DateTime.now());
  String? get lastError => errorForDay(DateTime.now());

    int get totalCalories => totalCaloriesForDay(DateTime.now());
    double get totalProtein => totalProteinForDay(DateTime.now());
    double get totalCarbs => totalCarbsForDay(DateTime.now());
    double get totalFat => totalFatForDay(DateTime.now());

  MealProvider(this._api);

  List<MealEntry> mealsForDay(DateTime day) {
    final key = _dayKey(day);
    return List.unmodifiable(_mealsByDay[key] ?? const <MealEntry>[]);
  }

    int totalCaloriesForDay(DateTime day) =>
      mealsForDay(day).fold(0, (sum, meal) => sum + meal.calories);

    double totalProteinForDay(DateTime day) =>
      mealsForDay(day).fold(0.0, (sum, meal) => sum + meal.proteinG);

    double totalCarbsForDay(DateTime day) =>
      mealsForDay(day).fold(0.0, (sum, meal) => sum + meal.carbsG);

    double totalFatForDay(DateTime day) =>
      mealsForDay(day).fold(0.0, (sum, meal) => sum + meal.fatG);

  bool isLoadingDay(DateTime day) => _loadingDays.contains(_dayKey(day));

  String? errorForDay(DateTime day) => _errorsByDay[_dayKey(day)];

  Future<void> loadToday() => loadDay(DateTime.now());

  Future<void> loadDay(DateTime day) async {
    final key = _dayKey(day);
    _loadingDays.add(key);
    _errorsByDay.remove(key);
    notifyListeners();
    try {
      final meals = await _api.getNutrition(day, day);
      _mealsByDay[key] = meals[key] ?? <MealEntry>[];
    } catch (e) {
      _errorsByDay[key] = _formatError(e);
    } finally {
      _loadingDays.remove(key);
      notifyListeners();
    }
  }

  /// Loads meals for every day in [start]..[end] (inclusive) in a single
  /// API call, merging results into the existing per-day cache.
  Future<void> loadRange(DateTime start, DateTime end) async {
    try {
      final meals = await _api.getNutrition(start, end);
      _mealsByDay.addAll(meals);
    } catch (_) {
      // Keep existing data on error.
    } finally {
      notifyListeners();
    }
  }

  Future<void> addMeal(MealEntry meal) async {
    final savedMeal = await _api.postMeal(meal);
    final key = _dayKey(savedMeal.timestamp);
    final meals = List<MealEntry>.from(_mealsByDay[key] ?? const <MealEntry>[])
      ..add(savedMeal);
    _mealsByDay[key] = meals;
    _errorsByDay.remove(key);
    // Track in local frequency cache
    await _frequentFoods.record(savedMeal);
    notifyListeners();
  }

  Future<void> addMealCopy(MealEntry meal, {DateTime? timestamp}) async {
    final effectiveTimestamp = timestamp ?? DateTime.now();
    final copiedMeal = MealEntry(
      foodName: meal.foodName,
      calories: meal.calories,
      proteinG: meal.proteinG,
      carbsG: meal.carbsG,
      fatG: meal.fatG,
      fiberG: meal.fiberG,
      portionDescription: meal.portionDescription,
      source: meal.source,
      timestamp: effectiveTimestamp,
      synced: meal.synced,
    );
    await addMeal(copiedMeal);
  }

  Future<List<MealEntry>> analyzeText(String text) => _api.analyzeText(text);

  Future<List<MealEntry>> analyzeImage(Uint8List imageBytes, {String? description}) =>
      _api.analyzeImage(imageBytes, description: description);

    Future<List<MealEntry>> lookupBarcode(String barcode) =>
      _api.lookupBarcode(barcode);

  Future<void> loadRecents({int limit = 10}) async {
    _recentMeals = await _api.getRecents(limit: limit);
    notifyListeners();
  }

  Future<void> loadFrequentFoods() async {
    await _frequentFoods.load();
    // Seed from API history on first run (empty local cache)
    if (_frequentFoods.foods.isEmpty) {
      try {
        final recents = await _api.getRecents(limit: 30);
        for (final meal in recents) {
          await _frequentFoods.record(meal);
        }
      } catch (_) {
        // Offline or API error — will seed next time
      }
    }
    notifyListeners();
  }

  Future<void> copyMealsFromDay(DateTime sourceDay, DateTime targetDay) async {
    final sourceMeals = List<MealEntry>.from(mealsForDay(sourceDay));
    if (sourceMeals.isEmpty) {
      return;
    }

    final targetKey = _dayKey(targetDay);
    final updatedMeals = List<MealEntry>.from(_mealsByDay[targetKey] ?? const <MealEntry>[])
      ..addAll(sourceMeals.map((meal) => MealEntry(
            foodName: meal.foodName,
            calories: meal.calories,
            proteinG: meal.proteinG,
            carbsG: meal.carbsG,
            fatG: meal.fatG,
            fiberG: meal.fiberG,
            portionDescription: meal.portionDescription,
            source: meal.source,
            timestamp: DateTime(
              targetDay.year,
              targetDay.month,
              targetDay.day,
              meal.timestamp.hour,
              meal.timestamp.minute,
              meal.timestamp.second,
              meal.timestamp.millisecond,
              meal.timestamp.microsecond,
            ),
            synced: meal.synced,
          )));

    _mealsByDay[targetKey] = updatedMeals;
    _errorsByDay.remove(targetKey);
    notifyListeners();
    await _syncMealsToApi(targetDay);
  }

  Future<void> removeMeal(DateTime day, int index) async {
    final key = _dayKey(day);
    final meals = List<MealEntry>.from(_mealsByDay[key] ?? const <MealEntry>[]);
    if (index < 0 || index >= meals.length) {
      return;
    }

    meals.removeAt(index);
    _mealsByDay[key] = meals;
    _errorsByDay.remove(key);
    notifyListeners();
    await _syncMealsToApi(day);
  }

  Future<void> updateMeal(DateTime day, int index, MealEntry updated) async {
    final key = _dayKey(day);
    final meals = List<MealEntry>.from(_mealsByDay[key] ?? const <MealEntry>[]);
    if (index < 0 || index >= meals.length) {
      return;
    }

    meals[index] = updated;
    _mealsByDay[key] = meals;
    _errorsByDay.remove(key);
    notifyListeners();
    await _syncMealsToApi(day);
  }

  Future<void> _syncMealsToApi(DateTime day) async {
    final key = _dayKey(day);
    try {
      await _api.putMeals(day, mealsForDay(day));
      _errorsByDay.remove(key);
    } catch (error) {
      _errorsByDay[key] = _formatError(error);
    } finally {
      notifyListeners();
    }
  }

  String _dayKey(DateTime day) =>
      '${day.year}-${day.month.toString().padLeft(2, '0')}-${day.day.toString().padLeft(2, '0')}';

  // ── Day Tracking Overrides & Weekly Balance ─────────────

  Future<void> loadDayOverrides() async {
    final overrides = await _api.getDayOverrides();
    _overridesByDay
      ..clear()
      ..addEntries(overrides.map((o) => MapEntry(_dayKey(o.date), o)));
    notifyListeners();
  }

  /// Whether [day] counts towards balance calculations: an explicit override
  /// takes precedence, otherwise a day with at least one logged meal is
  /// considered tracked.
  bool isDayTracked(DateTime day) {
    final override = _overridesByDay[_dayKey(day)];
    if (override != null) {
      return override.tracked;
    }
    return mealsForDay(day).isNotEmpty;
  }

  /// Whether [day] has an explicit tracking override set (regardless of its
  /// value). Used to decide whether a UI toggle should offer to "set" or
  /// "undo" the override.
  bool hasManualOverride(DateTime day) => _overridesByDay.containsKey(_dayKey(day));

  /// Flips whether [day] counts in balance calculations and persists it.
  Future<void> toggleDayOverride(DateTime day) async {
    final key = _dayKey(day);
    final newTracked = !isDayTracked(day);
    final existingNote = _overridesByDay[key]?.note ?? '';
    _overridesByDay[key] = DayTrackingOverride(
      date: DateTime(day.year, day.month, day.day),
      tracked: newTracked,
      note: existingNote,
      updatedAt: DateTime.now(),
    );
    notifyListeners();
    await _api.postDayOverride(day, newTracked, note: existingNote.isEmpty ? null : existingNote);
  }

  int _caloriesTargetForDay(DateTime day, NutritionGoal goal) {
    final isRest = NutritionGoal.isRestDay(day);
    return (isRest && goal.restCaloriesTarget != null) ? goal.restCaloriesTarget! : goal.caloriesTarget;
  }

  /// Sum of (actual - target) calories over the last 7 days (today back 6),
  /// skipping untracked days entirely. Returns null when [goal] is null.
  int? rollingWeekBalance(NutritionGoal? goal) {
    if (goal == null) return null;
    final today = DateTime.now();
    final start = DateTime(today.year, today.month, today.day);
    var balance = 0;
    for (var i = 0; i < 7; i++) {
      final day = start.subtract(Duration(days: i));
      if (!isDayTracked(day)) continue;
      balance += totalCaloriesForDay(day) - _caloriesTargetForDay(day, goal);
    }
    return balance;
  }

  /// How many of the last 7 days (today back 6) are tracked.
  int rollingWeekTrackedCount() {
    final today = DateTime.now();
    final start = DateTime(today.year, today.month, today.day);
    var count = 0;
    for (var i = 0; i < 7; i++) {
      if (isDayTracked(start.subtract(Duration(days: i)))) count++;
    }
    return count;
  }

  /// Status of [day], used by both the dashboard rolling bar and the
  /// history calendar row.
  DayStatus statusForDay(DateTime day, NutritionGoal? goal) {
    final today = DateTime.now();
    final normalizedToday = DateTime(today.year, today.month, today.day);
    final normalizedDay = DateTime(day.year, day.month, day.day);

    if (normalizedDay.isAfter(normalizedToday)) {
      return DayStatus.future;
    }
    if (!isDayTracked(day)) {
      return DayStatus.untracked;
    }
    if (goal == null) {
      return DayStatus.trackedWithinBudget;
    }
    final exceeded = totalCaloriesForDay(day) > _caloriesTargetForDay(day, goal);
    return exceeded ? DayStatus.trackedExceeded : DayStatus.trackedWithinBudget;
  }

  String _formatError(Object error) {
    if (error is ApiException) {
      try {
        final decoded = jsonDecode(error.body);
        if (decoded is Map<String, dynamic> && decoded['error'] is String) {
          return decoded['error'] as String;
        }
      } catch (_) {
        return error.toString();
      }
    }
    return error.toString();
  }
}
