import 'nutrition_source.dart';

/// A single food item logged by the user.
/// Mirrors Python MealEntry model.
class MealEntry {
  final String foodName;
  final int calories;
  final double proteinG;
  final double carbsG;
  final double fatG;
  final double? fiberG;
  final String? portionDescription;
  final NutritionSource source;
  final DateTime timestamp;
  final bool synced;

  const MealEntry({
    required this.foodName,
    required this.calories,
    required this.proteinG,
    required this.carbsG,
    required this.fatG,
    this.fiberG,
    this.portionDescription,
    required this.source,
    required this.timestamp,
    this.synced = false,
  });

  Map<String, dynamic> toJson() => {
        'food_name': foodName,
        'calories': calories,
        'protein_g': proteinG,
        'carbs_g': carbsG,
        'fat_g': fatG,
        if (fiberG != null) 'fiber_g': fiberG,
        if (portionDescription != null)
          'portion_description': portionDescription,
        'source': source.toJson(),
        'timestamp': timestamp.toIso8601String(),
      };

  factory MealEntry.fromJson(Map<String, dynamic> json) => MealEntry(
        foodName: json['food_name'] as String,
        calories: json['calories'] as int,
        proteinG: (json['protein_g'] as num).toDouble(),
        carbsG: (json['carbs_g'] as num).toDouble(),
        fatG: (json['fat_g'] as num).toDouble(),
        fiberG: (json['fiber_g'] as num?)?.toDouble(),
        portionDescription: json['portion_description'] as String?,
        source: NutritionSource.fromJson(json['source'] as String),
        timestamp: DateTime.parse(json['timestamp'] as String),
      );

  MealEntry copyWith({bool? synced}) => MealEntry(
        foodName: foodName,
        calories: calories,
        proteinG: proteinG,
        carbsG: carbsG,
        fatG: fatG,
        fiberG: fiberG,
        portionDescription: portionDescription,
        source: source,
        timestamp: timestamp,
        synced: synced ?? this.synced,
      );
}
