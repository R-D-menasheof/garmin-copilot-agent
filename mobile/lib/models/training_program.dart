class TrainingSession {
  final String day;
  final String type;
  final String description;
  final int durationMin;
  final int? targetHrZone;
  final bool completed;

  const TrainingSession({
    required this.day,
    required this.type,
    this.description = '',
    this.durationMin = 0,
    this.targetHrZone,
    this.completed = false,
  });

  factory TrainingSession.fromJson(Map<String, dynamic> json) => TrainingSession(
        day: json['day'] as String,
        type: json['type'] as String,
        description: (json['description'] as String?) ?? '',
        durationMin: (json['duration_min'] as int?) ?? 0,
        targetHrZone: json['target_hr_zone'] as int?,
        completed: (json['completed'] as bool?) ?? false,
      );

  Map<String, dynamic> toJson() => {
        'day': day,
        'type': type,
        'description': description,
        'duration_min': durationMin,
        'target_hr_zone': targetHrZone,
        'completed': completed,
      };

  TrainingSession copyWith({bool? completed}) => TrainingSession(
        day: day,
        type: type,
        description: description,
        durationMin: durationMin,
        targetHrZone: targetHrZone,
        completed: completed ?? this.completed,
      );
}

class TrainingWeek {
  final int weekNumber;
  final List<TrainingSession> sessions;
  final String notes;

  const TrainingWeek({
    required this.weekNumber,
    this.sessions = const [],
    this.notes = '',
  });

  factory TrainingWeek.fromJson(Map<String, dynamic> json) => TrainingWeek(
        weekNumber: json['week_number'] as int,
        sessions: (json['sessions'] as List? ?? [])
            .map((s) => TrainingSession.fromJson(s as Map<String, dynamic>))
            .toList(),
        notes: (json['notes'] as String?) ?? '',
      );

  Map<String, dynamic> toJson() => {
        'week_number': weekNumber,
        'sessions': sessions.map((s) => s.toJson()).toList(),
        'notes': notes,
      };
}

class TrainingProgram {
  final String id;
  final String name;
  final String goal;
  final int durationWeeks;
  final List<TrainingWeek> weeks;
  final DateTime createdAt;
  final bool active;

  const TrainingProgram({
    required this.id,
    required this.name,
    required this.goal,
    required this.durationWeeks,
    this.weeks = const [],
    required this.createdAt,
    this.active = true,
  });

  factory TrainingProgram.fromJson(Map<String, dynamic> json) => TrainingProgram(
        id: json['id'] as String,
        name: json['name'] as String,
        goal: json['goal'] as String,
        durationWeeks: json['duration_weeks'] as int,
        weeks: (json['weeks'] as List? ?? [])
            .map((w) => TrainingWeek.fromJson(w as Map<String, dynamic>))
            .toList(),
        createdAt: DateTime.parse(json['created_at'] as String),
        active: (json['active'] as bool?) ?? true,
      );

  Map<String, dynamic> toJson() => {
        'id': id,
        'name': name,
        'goal': goal,
        'duration_weeks': durationWeeks,
        'weeks': weeks.map((w) => w.toJson()).toList(),
        'created_at': createdAt.toIso8601String(),
        'active': active,
      };
}
