class Milestone {
  final String titleHe;
  final String targetMetric;
  final double targetValue;
  final double currentValue;
  final DateTime? deadline;
  final bool completed;

  const Milestone({
    required this.titleHe,
    this.targetMetric = '',
    this.targetValue = 0,
    this.currentValue = 0,
    this.deadline,
    this.completed = false,
  });

  factory Milestone.fromJson(Map<String, dynamic> json) => Milestone(
        titleHe: json['title_he'] as String,
        targetMetric: (json['target_metric'] as String?) ?? '',
        targetValue: (json['target_value'] as num?)?.toDouble() ?? 0,
        currentValue: (json['current_value'] as num?)?.toDouble() ?? 0,
        deadline: json['deadline'] != null
            ? DateTime.parse(json['deadline'] as String)
            : null,
        completed: (json['completed'] as bool?) ?? false,
      );

  Map<String, dynamic> toJson() => {
        'title_he': titleHe,
        'target_metric': targetMetric,
        'target_value': targetValue,
        'current_value': currentValue,
        'deadline': deadline?.toIso8601String().split('T').first,
        'completed': completed,
      };
}

class GoalProgram {
  final String id;
  final String nameHe;
  final String descriptionHe;
  final int durationWeeks;
  final List<Milestone> milestones;
  final DateTime startedAt;
  final double progressPct;
  final bool active;

  const GoalProgram({
    required this.id,
    required this.nameHe,
    this.descriptionHe = '',
    this.durationWeeks = 0,
    this.milestones = const [],
    required this.startedAt,
    this.progressPct = 0.0,
    this.active = true,
  });

  factory GoalProgram.fromJson(Map<String, dynamic> json) => GoalProgram(
        id: json['id'] as String,
        nameHe: json['name_he'] as String,
        descriptionHe: (json['description_he'] as String?) ?? '',
        durationWeeks: (json['duration_weeks'] as int?) ?? 0,
        milestones: (json['milestones'] as List? ?? [])
            .map((m) => Milestone.fromJson(m as Map<String, dynamic>))
            .toList(),
        startedAt: DateTime.parse(json['started_at'] as String),
        progressPct: (json['progress_pct'] as num?)?.toDouble() ?? 0.0,
        active: (json['active'] as bool?) ?? true,
      );

  Map<String, dynamic> toJson() => {
        'id': id,
        'name_he': nameHe,
        'description_he': descriptionHe,
        'duration_weeks': durationWeeks,
        'milestones': milestones.map((m) => m.toJson()).toList(),
        'started_at': startedAt.toIso8601String(),
        'progress_pct': progressPct,
        'active': active,
      };
}
