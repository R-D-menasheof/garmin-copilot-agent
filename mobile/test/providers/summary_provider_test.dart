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

    test('extractTrendData returns time series for key metrics', () async {
      final mockClient = MockClient((req) async {
        return http.Response(
          jsonEncode({
            'summaries': [
              {
                'date': '2026-04-04',
                'period_start': '2026-03-29',
                'period_end': '2026-04-04',
                'metrics_snapshot': {
                  'avg_resting_hr': 64,
                  'avg_hrv_nightly': 29,
                  'avg_sleep_hours': 6.3,
                  'weight_kg': 112.0,
                  'avg_daily_steps': 9000,
                  'avg_body_battery_peak': 56,
                },
                'trends': [],
                'recommendations': [],
                'context_for_next_run': '',
              },
              {
                'date': '2026-03-28',
                'period_start': '2026-03-21',
                'period_end': '2026-03-28',
                'metrics_snapshot': {
                  'avg_resting_hr': 65,
                  'avg_hrv_nightly': 28,
                  'avg_sleep_hours': 7.0,
                  'weight_kg': 113.0,
                  'avg_daily_steps': 8500,
                  'avg_body_battery_peak': 52,
                },
                'trends': [],
                'recommendations': [],
                'context_for_next_run': '',
              },
            ]
          }),
          200,
          headers: {'content-type': 'application/json; charset=utf-8'},
        );
      });

      final provider = SummaryProvider(
        ApiClient(baseUrl: 'http://test/api', apiKey: 'key', httpClient: mockClient),
      );
      await provider.loadSummaryHistory(limit: 8);

      final trends = provider.extractTrendData();
      expect(trends.keys, containsAll([
        'avg_resting_hr',
        'avg_hrv_nightly',
        'avg_sleep_hours',
        'weight_kg',
        'avg_daily_steps',
        'avg_body_battery_peak',
      ]));
      expect(trends['avg_resting_hr']!, hasLength(2));
      // Should be sorted by date (oldest first)
      expect(trends['avg_resting_hr']!.first.$2, 65);
      expect(trends['avg_resting_hr']!.last.$2, 64);
    });
  });
}