import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

import '../models/meal_entry.dart';
import '../models/nutrition_source.dart';

/// Locally cached food frequency tracker.
///
/// Every logged meal automatically updates the frequency map.
/// Foods are scored by frequency + recency and sorted highest first.
/// Stored in SharedPreferences — survives app restarts, no API calls.
class FrequentFoodsService {
  static const _key = 'vitalis_frequent_foods';
  static const _maxItems = 50;

  /// In-memory cache of food entries with usage stats.
  List<FrequentFood> _foods = [];
  List<FrequentFood> get foods => List.unmodifiable(_foods);

  /// Load from SharedPreferences.
  Future<void> load() async {
    final prefs = await SharedPreferences.getInstance();
    final raw = prefs.getString(_key);
    if (raw == null) {
      _foods = [];
      return;
    }
    try {
      final list = jsonDecode(raw) as List;
      _foods = list.map((e) => FrequentFood.fromJson(e as Map<String, dynamic>)).toList();
      _sort();
    } catch (_) {
      _foods = [];
    }
  }

  /// Record a meal. Call after every successful addMeal().
  Future<void> record(MealEntry meal) async {
    final normalized = meal.foodName.trim().toLowerCase();
    final idx = _foods.indexWhere((f) => f.normalizedName == normalized);

    if (idx >= 0) {
      // Update existing
      _foods[idx] = _foods[idx].copyWith(
        count: _foods[idx].count + 1,
        lastUsed: DateTime.now(),
        // Update nutrition in case it changed
        calories: meal.calories,
        proteinG: meal.proteinG,
        carbsG: meal.carbsG,
        fatG: meal.fatG,
        portionDescription: meal.portionDescription,
      );
    } else {
      // Add new
      _foods.add(FrequentFood(
        foodName: meal.foodName,
        normalizedName: normalized,
        calories: meal.calories,
        proteinG: meal.proteinG,
        carbsG: meal.carbsG,
        fatG: meal.fatG,
        portionDescription: meal.portionDescription,
        count: 1,
        lastUsed: DateTime.now(),
      ));
    }

    _sort();
    _evict();
    await _save();
  }

  /// Get top N foods sorted by score (frequency + recency).
  List<FrequentFood> topN(int n) => _foods.take(n).toList();

  /// Search foods by partial name match.
  List<FrequentFood> search(String query) {
    if (query.isEmpty) return [];
    final q = query.trim().toLowerCase();
    return _foods.where((f) => f.normalizedName.contains(q)).toList();
  }

  void _sort() {
    final now = DateTime.now();
    _foods.sort((a, b) => b._score(now).compareTo(a._score(now)));
  }

  void _evict() {
    if (_foods.length > _maxItems) {
      _foods = _foods.sublist(0, _maxItems);
    }
  }

  Future<void> _save() async {
    final prefs = await SharedPreferences.getInstance();
    final data = jsonEncode(_foods.map((f) => f.toJson()).toList());
    await prefs.setString(_key, data);
  }
}

/// A food item with usage frequency and nutrition data.
class FrequentFood {
  final String foodName;
  final String normalizedName;
  final int calories;
  final double proteinG;
  final double carbsG;
  final double fatG;
  final String? portionDescription;
  final int count;
  final DateTime lastUsed;

  const FrequentFood({
    required this.foodName,
    required this.normalizedName,
    required this.calories,
    required this.proteinG,
    required this.carbsG,
    required this.fatG,
    this.portionDescription,
    required this.count,
    required this.lastUsed,
  });

  /// Score combines frequency (count) with recency decay.
  /// Recent items get a boost; old items decay.
  double _score(DateTime now) {
    final daysSince = now.difference(lastUsed).inDays.clamp(0, 365);
    final recencyBoost = 1.0 / (1.0 + daysSince / 7.0); // halves every 7 days
    return count * recencyBoost;
  }

  FrequentFood copyWith({
    int? count,
    DateTime? lastUsed,
    int? calories,
    double? proteinG,
    double? carbsG,
    double? fatG,
    String? portionDescription,
  }) =>
      FrequentFood(
        foodName: foodName,
        normalizedName: normalizedName,
        calories: calories ?? this.calories,
        proteinG: proteinG ?? this.proteinG,
        carbsG: carbsG ?? this.carbsG,
        fatG: fatG ?? this.fatG,
        portionDescription: portionDescription ?? this.portionDescription,
        count: count ?? this.count,
        lastUsed: lastUsed ?? this.lastUsed,
      );

  factory FrequentFood.fromJson(Map<String, dynamic> json) => FrequentFood(
        foodName: json['food_name'] as String,
        normalizedName: json['normalized_name'] as String,
        calories: json['calories'] as int,
        proteinG: (json['protein_g'] as num).toDouble(),
        carbsG: (json['carbs_g'] as num).toDouble(),
        fatG: (json['fat_g'] as num).toDouble(),
        portionDescription: json['portion_description'] as String?,
        count: json['count'] as int,
        lastUsed: DateTime.parse(json['last_used'] as String),
      );

  Map<String, dynamic> toJson() => {
        'food_name': foodName,
        'normalized_name': normalizedName,
        'calories': calories,
        'protein_g': proteinG,
        'carbs_g': carbsG,
        'fat_g': fatG,
        'portion_description': portionDescription,
        'count': count,
        'last_used': lastUsed.toIso8601String(),
      };

  /// Convert back to a MealEntry for re-logging.
  MealEntry toMealEntry({DateTime? timestamp}) => MealEntry(
        foodName: foodName,
        calories: calories,
        proteinG: proteinG,
        carbsG: carbsG,
        fatG: fatG,
        portionDescription: portionDescription,
        source: NutritionSource.history,
        timestamp: timestamp ?? DateTime.now(),
      );
}
