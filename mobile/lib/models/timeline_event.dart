class TimelineEvent {
  final DateTime date;
  final String category; // medical, milestone, medication, lifestyle
  final String titleHe;
  final String detailHe;
  final String icon;
  final String severity; // info, warning, critical, positive
  final String source;

  const TimelineEvent({
    required this.date,
    required this.category,
    required this.titleHe,
    this.detailHe = '',
    this.icon = '',
    this.severity = 'info',
    this.source = 'agent',
  });

  factory TimelineEvent.fromJson(Map<String, dynamic> json) => TimelineEvent(
        date: DateTime.parse(json['date'] as String),
        category: json['category'] as String,
        titleHe: json['title_he'] as String,
        detailHe: (json['detail_he'] as String?) ?? '',
        icon: (json['icon'] as String?) ?? '',
        severity: (json['severity'] as String?) ?? 'info',
        source: (json['source'] as String?) ?? 'agent',
      );

  Map<String, dynamic> toJson() => {
        'date': date.toIso8601String().split('T').first,
        'category': category,
        'title_he': titleHe,
        'detail_he': detailHe,
        'icon': icon,
        'severity': severity,
        'source': source,
      };
}
