import 'package:flutter_test/flutter_test.dart';

import 'package:vitalis/models/analysis_summary.dart';
import 'package:vitalis/models/health_recommendation.dart';

Map<String, dynamic> _sampleJson({String? reportMarkdown}) => {
      'date': '2026-04-04',
      'period_start': '2026-03-28',
      'period_end': '2026-04-04',
      'metrics_snapshot': {'avg_daily_steps': 9000},
      'trends': ['Steps improving'],
      'recommendations': [
        {
          'category': 'sleep',
          'title': 'Extend sleep to 7h',
          'detail': 'Average 6.3h',
          'priority': 1,
        },
      ],
      'context_for_next_run': 'HRV baseline 29ms',
      if (reportMarkdown != null) 'report_markdown': reportMarkdown,
    };

void main() {
  group('AnalysisSummary', () {
    test('fromJson round-trip with reportMarkdown', () {
      const md = '# דו"ח בריאות\n\nתוכן בעברית...';
      final json = _sampleJson(reportMarkdown: md);
      final summary = AnalysisSummary.fromJson(json);

      expect(summary.reportMarkdown, md);
      expect(summary.recommendations, hasLength(1));

      final restored = AnalysisSummary.fromJson(summary.toJson());
      expect(restored.reportMarkdown, md);
    });

    test('fromJson without reportMarkdown defaults to empty string', () {
      final json = _sampleJson();
      final summary = AnalysisSummary.fromJson(json);

      expect(summary.reportMarkdown, '');
      expect(summary.date, DateTime(2026, 4, 4));
    });

    test('toJson includes reportMarkdown field', () {
      const md = '# Report';
      final summary = AnalysisSummary.fromJson(_sampleJson(reportMarkdown: md));
      final json = summary.toJson();

      expect(json['report_markdown'], md);
    });
  });
}
