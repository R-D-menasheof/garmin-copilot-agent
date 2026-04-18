/// Daily nutrition targets set by user or External Agent.
/// Mirrors Python NutritionGoal model.
class NutritionGoal {
  final DateTime date;
  final int caloriesTarget;
  final double proteinGTarget;
  final double carbsGTarget;
  final double fatGTarget;
  final int? restCaloriesTarget;
  final double? restCarbsGTarget;
  final String setBy;

  const NutritionGoal({
    required this.date,
    required this.caloriesTarget,
    required this.proteinGTarget,
    required this.carbsGTarget,
    required this.fatGTarget,
    this.restCaloriesTarget,
    this.restCarbsGTarget,
    required this.setBy,
  });

  factory NutritionGoal.fromJson(Map<String, dynamic> json) => NutritionGoal(
        date: DateTime.parse(json['date'] as String),
        caloriesTarget: json['calories_target'] as int,
        proteinGTarget: (json['protein_g_target'] as num).toDouble(),
        carbsGTarget: (json['carbs_g_target'] as num).toDouble(),
        fatGTarget: (json['fat_g_target'] as num).toDouble(),
        restCaloriesTarget: json['rest_calories_target'] as int?,
        restCarbsGTarget: (json['rest_carbs_g_target'] as num?)?.toDouble(),
        setBy: json['set_by'] as String,
      );

  /// Whether [day] is a rest day (Friday or Saturday).
  static bool isRestDay([DateTime? day]) {
    final d = day ?? DateTime.now();
    return d.weekday == DateTime.friday || d.weekday == DateTime.saturday;
  }

  /// Calorie target for today (uses rest-day target on Fri/Sat if set).
  int get todayCaloriesTarget =>
      isRestDay() && restCaloriesTarget != null
          ? restCaloriesTarget!
          : caloriesTarget;

  /// Carbs target for today (uses rest-day target on Fri/Sat if set).
  double get todayCarbsGTarget =>
      isRestDay() && restCarbsGTarget != null
          ? restCarbsGTarget!
          : carbsGTarget;

  Map<String, dynamic> toJson() => {
        'date': date.toIso8601String().split('T').first,
        'calories_target': caloriesTarget,
        'protein_g_target': proteinGTarget,
        'carbs_g_target': carbsGTarget,
        'fat_g_target': fatGTarget,
        if (restCaloriesTarget != null)
          'rest_calories_target': restCaloriesTarget,
        if (restCarbsGTarget != null) 'rest_carbs_g_target': restCarbsGTarget,
        'set_by': setBy,
      };
}
