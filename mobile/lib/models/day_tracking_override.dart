/// Marks a day's nutrition log as unreliable/not representative.
///
/// Used to exclude a day from weekly balance calculations without
/// deleting any logged meals (e.g. "I forgot to log properly today").
class DayTrackingOverride {
  final DateTime date;
  final bool tracked;
  final String note;
  final DateTime updatedAt;

  const DayTrackingOverride({
    required this.date,
    this.tracked = true,
    this.note = '',
    required this.updatedAt,
  });

  factory DayTrackingOverride.fromJson(Map<String, dynamic> json) =>
      DayTrackingOverride(
        date: DateTime.parse(json['date'] as String),
        tracked: json['tracked'] as bool? ?? true,
        note: json['note'] as String? ?? '',
        updatedAt: DateTime.parse(json['updated_at'] as String),
      );

  Map<String, dynamic> toJson() => {
        'date': _formatDate(date),
        'tracked': tracked,
        'note': note,
        'updated_at': updatedAt.toIso8601String(),
      };

  static String _formatDate(DateTime date) =>
      '${date.year.toString().padLeft(4, '0')}-'
      '${date.month.toString().padLeft(2, '0')}-'
      '${date.day.toString().padLeft(2, '0')}';

  DayTrackingOverride copyWith({bool? tracked, String? note, DateTime? updatedAt}) =>
      DayTrackingOverride(
        date: date,
        tracked: tracked ?? this.tracked,
        note: note ?? this.note,
        updatedAt: updatedAt ?? this.updatedAt,
      );
}
