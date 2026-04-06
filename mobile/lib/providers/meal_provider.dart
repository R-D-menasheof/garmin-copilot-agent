import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter/foundation.dart';

import '../models/meal_entry.dart';
import '../services/api_client.dart';

/// State management for meal logging and daily totals.
class MealProvider extends ChangeNotifier {
  final ApiClient _api;

  final Map<String, List<MealEntry>> _mealsByDay = <String, List<MealEntry>>{};
  final Set<String> _loadingDays = <String>{};
  final Map<String, String?> _errorsByDay = <String, String?>{};
  List<MealEntry> _recentMeals = <MealEntry>[];

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

  Future<void> addMeal(MealEntry meal) async {
    final savedMeal = await _api.postMeal(meal);
    final key = _dayKey(savedMeal.timestamp);
    final meals = List<MealEntry>.from(_mealsByDay[key] ?? const <MealEntry>[])
      ..add(savedMeal);
    _mealsByDay[key] = meals;
    _errorsByDay.remove(key);
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

  Future<List<MealEntry>> analyzeImage(Uint8List imageBytes) =>
      _api.analyzeImage(imageBytes);

    Future<List<MealEntry>> lookupBarcode(String barcode) =>
      _api.lookupBarcode(barcode);

  Future<void> loadRecents({int limit = 10}) async {
    _recentMeals = await _api.getRecents(limit: limit);
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
