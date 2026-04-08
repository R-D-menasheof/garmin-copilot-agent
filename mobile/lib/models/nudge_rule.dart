class NudgeRule {
  final String condition;
  final String messageHe;
  final String category;
  final int priority;

  const NudgeRule({
    required this.condition,
    required this.messageHe,
    required this.category,
    this.priority = 3,
  });

  factory NudgeRule.fromJson(Map<String, dynamic> json) => NudgeRule(
        condition: json['condition'] as String,
        messageHe: json['message_he'] as String,
        category: json['category'] as String,
        priority: (json['priority'] as int?) ?? 3,
      );

  Map<String, dynamic> toJson() => {
        'condition': condition,
        'message_he': messageHe,
        'category': category,
        'priority': priority,
      };
}
