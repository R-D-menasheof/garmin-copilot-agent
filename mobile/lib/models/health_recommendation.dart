class HealthRecommendation {
  final String category;
  final String title;
  final String detail;
  final int priority;

  const HealthRecommendation({
    required this.category,
    required this.title,
    required this.detail,
    required this.priority,
  });

  factory HealthRecommendation.fromJson(Map<String, dynamic> json) =>
      HealthRecommendation(
        category: json['category'] as String,
        title: json['title'] as String,
        detail: json['detail'] as String,
        priority: json['priority'] as int,
      );

  Map<String, dynamic> toJson() => {
        'category': category,
        'title': title,
        'detail': detail,
        'priority': priority,
      };
}