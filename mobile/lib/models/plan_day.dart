class PlanDay {
  final DateTime date;
  final List<String> templateIds;
  final String? notes;
  final DateTime createdAt;
  final DateTime updatedAt;

  const PlanDay({
    required this.date,
    required this.templateIds,
    this.notes,
    required this.createdAt,
    required this.updatedAt,
  });

  factory PlanDay.fromJson(Map<String, dynamic> json) => PlanDay(
        date: DateTime.parse(json['date'] as String),
        templateIds: (json['template_ids'] as List<dynamic>? ?? const <dynamic>[])
            .map((item) => item as String)
            .toList(),
        notes: json['notes'] as String?,
        createdAt: DateTime.parse(json['created_at'] as String),
        updatedAt: DateTime.parse(json['updated_at'] as String),
      );
}