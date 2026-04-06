import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:vitalis/providers/summary_provider.dart';
import 'package:vitalis/services/api_client.dart';

void main() {
  group('SummaryProvider', () {
    test('loadLatestSummary stores the latest published summary', () async {
      final mockClient = MockClient((req) async {
        return http.Response(
          jsonEncode({
            'summary': {
              'date': '2026-04-04',
              'period_start': '2026-03-29',
              'period_end': '2026-04-04',
              'metrics_snapshot': {'steps_avg': 8500},
              'trends': ['Average steps increased'],
              'recommendations': [
                {
                  'category': 'activity',
                  'title': 'Keep walking',
                  'detail': 'Maintain the current step streak.',
                  'priority': 2,
                }
              ],
              'context_for_next_run': 'Monitor recovery after hard sessions.',
            }
          }),
          200,
        );
      });

      final provider = SummaryProvider(
        ApiClient(
          baseUrl: 'http://test/api',
          apiKey: 'test-key',
          httpClient: mockClient,
        ),
      );

      await provider.loadLatestSummary();

      expect(provider.latestSummary, isNotNull);
      expect(provider.latestSummary!.metricsSnapshot['steps_avg'], 8500);
      expect(provider.latestSummary!.recommendations.single.title, 'Keep walking');
    });

    test('loadSummaryHistory stores published summaries', () async {
      final mockClient = MockClient((req) async {
        return http.Response(
          jsonEncode({
            'summaries': [
              {
                'date': '2026-04-04',
                'period_start': '2026-03-29',
                'period_end': '2026-04-04',
                'metrics_snapshot': {'steps_avg': 8500},
                'trends': ['Average steps increased'],
                'recommendations': [
                  {
                    'category': 'activity',
                    'title': 'Keep walking',
                    'detail': 'Maintain the current step streak.',
                    'priority': 2,
                  }
                ],
                'context_for_next_run': 'Monitor recovery after hard sessions.',
              }
            ]
          }),
          200,
        );
      });

      final provider = SummaryProvider(
        ApiClient(
          baseUrl: 'http://test/api',
          apiKey: 'test-key',
          httpClient: mockClient,
        ),
      );

      await provider.loadSummaryHistory(limit: 1);

      expect(provider.summaryHistory, hasLength(1));
      expect(provider.summaryHistory.single.trends.single, 'Average steps increased');
    });
  });
}