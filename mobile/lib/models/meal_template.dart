import 'meal_entry.dart';

class MealTemplate {
  final String id;
  final String name;
  final List<MealEntry> meals;
  final String? notes;
  final DateTime createdAt;

  const MealTemplate({
    required this.id,
    required this.name,
    required this.meals,
    this.notes,
    required this.createdAt,
  });

  factory MealTemplate.fromJson(Map<String, dynamic> json) => MealTemplate(
        id: json['id'] as String,
        name: json['name'] as String,
        meals: (json['meals'] as List)
            .map((item) => MealEntry.fromJson(item as Map<String, dynamic>))
            .toList(),
        notes: json['notes'] as String?,
        createdAt: DateTime.parse(json['created_at'] as String),
      );

  Map<String, dynamic> toJson() => {
        'id': id,
        'name': name,
        'meals': meals.map((meal) => meal.toJson()).toList(),
        if (notes != null) 'notes': notes,
        'created_at': createdAt.toIso8601String(),
      };
}