import 'health_recommendation.dart';
import 'nudge_rule.dart';
import 'health_data_models.dart';

class AnalysisSummary {
  final DateTime date;
  final DateTime periodStart;
  final DateTime periodEnd;
  final Map<String, dynamic> metricsSnapshot;
  final List<String> trends;
  final List<HealthRecommendation> recommendations;
  final String contextForNextRun;
  final String reportMarkdown;
  final List<NudgeRule> nudgeRules;
  final List<HealthCorrelation> correlations;

  const AnalysisSummary({
    required this.date,
    required this.periodStart,
    required this.periodEnd,
    required this.metricsSnapshot,
    required this.trends,
    required this.recommendations,
    required this.contextForNextRun,
    this.reportMarkdown = '',
    this.nudgeRules = const [],
    this.correlations = const [],
  });

  factory AnalysisSummary.fromJson(Map<String, dynamic> json) => AnalysisSummary(
        date: DateTime.parse(json['date'] as String),
        periodStart: DateTime.parse(json['period_start'] as String),
        periodEnd: DateTime.parse(json['period_end'] as String),
        metricsSnapshot: Map<String, dynamic>.from(
          json['metrics_snapshot'] as Map<String, dynamic>,
        ),
        trends: (json['trends'] as List).cast<String>(),
        recommendations: (json['recommendations'] as List)
            .map((item) => HealthRecommendation.fromJson(item as Map<String, dynamic>))
            .toList(),
        contextForNextRun: json['context_for_next_run'] as String,
        reportMarkdown: (json['report_markdown'] as String?) ?? '',
        nudgeRules: (json['nudge_rules'] as List? ?? [])
            .map((item) => NudgeRule.fromJson(item as Map<String, dynamic>))
            .toList(),
        correlations: (json['correlations'] as List? ?? [])
            .map((item) => HealthCorrelation.fromJson(item as Map<String, dynamic>))
            .toList(),
      );

  Map<String, dynamic> toJson() => {
        'date': date.toIso8601String().split('T').first,
        'period_start': periodStart.toIso8601String().split('T').first,
        'period_end': periodEnd.toIso8601String().split('T').first,
        'metrics_snapshot': metricsSnapshot,
        'trends': trends,
        'recommendations': recommendations.map((item) => item.toJson()).toList(),
        'context_for_next_run': contextForNextRun,
        'report_markdown': reportMarkdown,
        'nudge_rules': nudgeRules.map((r) => r.toJson()).toList(),
        'correlations': correlations.map((c) => c.toJson()).toList(),
      };
}