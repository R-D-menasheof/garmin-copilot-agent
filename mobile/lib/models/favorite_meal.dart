import 'meal_entry.dart';

class FavoriteMeal {
  final String id;
  final MealEntry meal;
  final String? label;
  final DateTime createdAt;

  const FavoriteMeal({
    required this.id,
    required this.meal,
    this.label,
    required this.createdAt,
  });

  String get displayName => label?.isNotEmpty == true ? label! : meal.foodName;

  factory FavoriteMeal.fromJson(Map<String, dynamic> json) => FavoriteMeal(
        id: json['id'] as String,
        meal: MealEntry.fromJson(json['meal'] as Map<String, dynamic>),
        label: json['label'] as String?,
        createdAt: DateTime.parse(json['created_at'] as String),
      );

  Map<String, dynamic> toJson() => {
        'id': id,
        'meal': meal.toJson(),
        if (label != null) 'label': label,
        'created_at': createdAt.toIso8601String(),
      };
}