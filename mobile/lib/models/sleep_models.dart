class ChecklistItem {
  final String id;
  final String labelHe;
  final String category;
  bool checked;

  ChecklistItem({
    required this.id,
    required this.labelHe,
    required this.category,
    this.checked = false,
  });

  factory ChecklistItem.fromJson(Map<String, dynamic> json) => ChecklistItem(
        id: json['id'] as String,
        labelHe: json['label_he'] as String,
        category: json['category'] as String,
        checked: (json['checked'] as bool?) ?? false,
      );

  Map<String, dynamic> toJson() => {
        'id': id,
        'label_he': labelHe,
        'category': category,
        'checked': checked,
      };
}

class SleepChecklist {
  final List<ChecklistItem> items;

  const SleepChecklist({this.items = const []});

  factory SleepChecklist.fromJson(Map<String, dynamic> json) => SleepChecklist(
        items: (json['items'] as List? ?? [])
            .map((i) => ChecklistItem.fromJson(i as Map<String, dynamic>))
            .toList(),
      );

  Map<String, dynamic> toJson() => {
        'items': items.map((i) => i.toJson()).toList(),
      };
}

class SleepEntry {
  final DateTime date;
  final String? bedtime;
  final String? waketime;
  final int rating;
  final String notes;
  final String? caffeineCutoff;
  final String? screenCutoff;
  final int checklistCompleted;

  const SleepEntry({
    required this.date,
    this.bedtime,
    this.waketime,
    this.rating = 3,
    this.notes = '',
    this.caffeineCutoff,
    this.screenCutoff,
    this.checklistCompleted = 0,
  });

  factory SleepEntry.fromJson(Map<String, dynamic> json) => SleepEntry(
        date: DateTime.parse(json['date'] as String),
        bedtime: json['bedtime'] as String?,
        waketime: json['waketime'] as String?,
        rating: (json['rating'] as int?) ?? 3,
        notes: (json['notes'] as String?) ?? '',
        caffeineCutoff: json['caffeine_cutoff'] as String?,
        screenCutoff: json['screen_cutoff'] as String?,
        checklistCompleted: (json['checklist_completed'] as int?) ?? 0,
      );

  Map<String, dynamic> toJson() => {
        'date': date.toIso8601String().split('T').first,
        'bedtime': bedtime,
        'waketime': waketime,
        'rating': rating,
        'notes': notes,
        'caffeine_cutoff': caffeineCutoff,
        'screen_cutoff': screenCutoff,
        'checklist_completed': checklistCompleted,
      };
}
