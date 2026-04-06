/// Nutrition data source — mirrors Python NutritionSource enum.
enum NutritionSource {
  history,
  openFoodFacts,
  usda,
  llm,
  manual;

  String toJson() => name;

  static NutritionSource fromJson(String value) {
    switch (value) {
      case 'history':
        return NutritionSource.history;
      case 'open_food_facts':
        return NutritionSource.openFoodFacts;
      case 'usda':
        return NutritionSource.usda;
      case 'llm':
        return NutritionSource.llm;
      case 'manual':
        return NutritionSource.manual;
      default:
        return NutritionSource.manual;
    }
  }
}
