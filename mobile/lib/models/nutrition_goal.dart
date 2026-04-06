/// Daily nutrition targets set by user or External Agent.
/// Mirrors Python NutritionGoal model.
class NutritionGoal {
  final DateTime date;
  final int caloriesTarget;
  final double proteinGTarget;
  final double carbsGTarget;
  final double fatGTarget;
  final String setBy;

  const NutritionGoal({
    required this.date,
    required this.caloriesTarget,
    required this.proteinGTarget,
    required this.carbsGTarget,
    required this.fatGTarget,
    required this.setBy,
  });

  factory NutritionGoal.fromJson(Map<String, dynamic> json) => NutritionGoal(
        date: DateTime.parse(json['date'] as String),
        caloriesTarget: json['calories_target'] as int,
        proteinGTarget: (json['protein_g_target'] as num).toDouble(),
        carbsGTarget: (json['carbs_g_target'] as num).toDouble(),
        fatGTarget: (json['fat_g_target'] as num).toDouble(),
        setBy: json['set_by'] as String,
      );

  Map<String, dynamic> toJson() => {
        'date': date.toIso8601String().split('T').first,
        'calories_target': caloriesTarget,
        'protein_g_target': proteinGTarget,
        'carbs_g_target': carbsGTarget,
        'fat_g_target': fatGTarget,
        'set_by': setBy,
      };
}
