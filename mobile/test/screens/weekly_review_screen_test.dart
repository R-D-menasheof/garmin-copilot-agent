import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:provider/provider.dart';

import 'package:vitalis/providers/recommendation_provider.dart';
import 'package:vitalis/providers/summary_provider.dart';
import 'package:vitalis/screens/weekly_review_screen.dart';
import 'package:vitalis/services/api_client.dart';

Map<String, dynamic> _summaryJson({String reportMarkdown = ''}) => {
      'date': '2026-04-04',
      'period_start': '2026-03-29',
      'period_end': '2026-04-04',
      'metrics_snapshot': {'steps_avg': 8500},
      'trends': ['Average steps increased'],
      'recommendations': [
        {
          'category': 'sleep',
          'title': 'Extend sleep to 7h',
          'detail': 'Average 6.3h — below target',
          'priority': 1,
        },
        {
          'category': 'fitness',
          'title': 'Keep swimming',
          'detail': 'Excellent consistency — 5x/14 days',
          'priority': 5,
        },
      ],
      'context_for_next_run': 'HRV baseline 29ms',
      'report_markdown': reportMarkdown,
    };

Widget _buildScreen(SummaryProvider provider) {
  final apiClient = ApiClient(
    baseUrl: 'http://test/api',
    apiKey: 'key',
    httpClient: MockClient((req) async {
      final uri = req.url;
      if (uri.path.contains('medical/lab-trends')) {
        return http.Response(
          jsonEncode({'trends': []}),
          200,
          headers: {'content-type': 'application/json; charset=utf-8'},
        );
      }
      return http.Response('{}', 404);
    }),
  );

  // Create a recommendation provider with a no-op API client
  final recMock = MockClient((req) async {
    if (req.method == 'GET') {
      return http.Response(jsonEncode({'statuses': []}), 200,
          headers: {'content-type': 'application/json; charset=utf-8'});
    }
    return http.Response(jsonEncode({'status': 'ok'}), 201);
  });
  final recProvider = RecommendationProvider(
    ApiClient(baseUrl: 'http://test/api', apiKey: 'key', httpClient: recMock),
  );
  return MultiProvider(
    providers: [
      Provider<ApiClient>.value(value: apiClient),
      ChangeNotifierProvider.value(value: provider),
      ChangeNotifierProvider.value(value: recProvider),
    ],
    child: const MaterialApp(home: WeeklyReviewScreen()),
  );
}

Widget _buildScreenWithLabTrends(
  SummaryProvider provider, {
  required List<Map<String, dynamic>> labTrends,
}) {
  final apiClient = ApiClient(
    baseUrl: 'http://test/api',
    apiKey: 'key',
    httpClient: MockClient((req) async {
      final uri = req.url;
      if (uri.path.contains('medical/lab-trends')) {
        return http.Response(
          jsonEncode({'trends': labTrends}),
          200,
          headers: {'content-type': 'application/json; charset=utf-8'},
        );
      }
      return http.Response('{}', 404);
    }),
  );

  final recMock = MockClient((req) async {
    if (req.method == 'GET') {
      return http.Response(jsonEncode({'statuses': []}), 200,
          headers: {'content-type': 'application/json; charset=utf-8'});
    }
    return http.Response(jsonEncode({'status': 'ok'}), 201);
  });
  final recProvider = RecommendationProvider(
    ApiClient(baseUrl: 'http://test/api', apiKey: 'key', httpClient: recMock),
  );

  return MultiProvider(
    providers: [
      Provider<ApiClient>.value(value: apiClient),
      ChangeNotifierProvider.value(value: provider),
      ChangeNotifierProvider.value(value: recProvider),
    ],
    child: const MaterialApp(home: WeeklyReviewScreen()),
  );
}

SummaryProvider _providerWith({String reportMarkdown = ''}) {
  final mockClient = MockClient((req) async {
    final uri = req.url;
    if (uri.path.contains('summary/latest')) {
      return http.Response(
        jsonEncode({'summary': _summaryJson(reportMarkdown: reportMarkdown)}),
        200,
        headers: {'content-type': 'application/json; charset=utf-8'},
      );
    }
    if (uri.path.contains('summary/history')) {
      return http.Response(
        jsonEncode({
          'summaries': [_summaryJson(reportMarkdown: reportMarkdown)]
        }),
        200,
        headers: {'content-type': 'application/json; charset=utf-8'},
      );
    }
    return http.Response('{}', 404);
  });

  return SummaryProvider(
    ApiClient(baseUrl: 'http://test/api', apiKey: 'key', httpClient: mockClient),
  );
}

void main() {
  group('WeeklyReviewScreen', () {
    testWidgets('displays three tabs', (tester) async {
      await tester.pumpWidget(_buildScreen(_providerWith()));
      await tester.pumpAndSettle();

      // Tab labels exist (משימות appears in both tab and section header)
      expect(find.text('משימות'), findsWidgets);
      expect(find.text('דוח'), findsOneWidget);
      expect(find.text('מגמות'), findsOneWidget);
    });

    testWidgets('defaults to todo tab showing recommendations', (tester) async {
      final provider = _providerWith();
      await provider.loadLatestSummary();

      // Debug: check for errors
      if (provider.error != null) {
        fail('Provider error during loadLatestSummary: ${provider.error}');
      }
      expect(provider.latestSummary, isNotNull,
          reason: 'Pre-load failed: latestSummary is null');

      await tester.pumpWidget(_buildScreen(provider));
      await tester.pump();

      // P1 action item shows in tasks section
      expect(find.text('Extend sleep to 7h'), findsOneWidget);
      // P5 shows in achievements section
      expect(find.text('Keep swimming'), findsOneWidget);
      // Section headers
      expect(find.text('משימות'), findsWidgets); // tab + section header
      expect(find.text('הישגים ✨'), findsOneWidget);
    });

    testWidgets('report tab renders markdown content', (tester) async {
      const md = '# Health Report\n\nSome **bold** text.';
      final provider = _providerWith(reportMarkdown: md);
      await provider.loadLatestSummary();

      await tester.pumpWidget(_buildScreen(provider));
      await tester.pump();

      // Switch to the report tab
      await tester.tap(find.text('דוח'));
      await tester.pumpAndSettle();

      expect(find.text('Health Report'), findsOneWidget);
    });

    testWidgets('trends tab shows placeholder', (tester) async {
      final provider = _providerWith();
      await provider.loadLatestSummary();

      await tester.pumpWidget(_buildScreen(provider));
      await tester.pump();

      await tester.tap(find.text('מגמות'));
      await tester.pumpAndSettle();

      expect(find.text('בקרוב'), findsOneWidget);
    });

    testWidgets('lab tab hides metrics with fewer than two points', (tester) async {
      final provider = _providerWith();
      await provider.loadLatestSummary();

      final labTrends = [
        {
          'metric': 'glucose',
          'display_name_he': 'גלוקוז',
          'values': [
            {
              'date': '2020-02-26',
              'value': 85,
              'unit': 'mg/dL',
              'reference_range': '70-100',
              'status': 'normal',
            },
            {
              'date': '2022-09-19',
              'value': 91,
              'unit': 'mg/dL',
              'reference_range': '70-100',
              'status': 'normal',
            },
          ],
        },
        {
          'metric': 'egfr',
          'display_name_he': 'תפקוד כליות (eGFR)',
          'values': [
            {
              'date': '2025-09-03',
              'value': 75,
              'unit': 'mL/min',
              'reference_range': '>90',
              'status': 'low',
            },
          ],
        },
      ];

      await tester.pumpWidget(
        _buildScreenWithLabTrends(provider, labTrends: labTrends),
      );
      await tester.pump();

      await tester.tap(find.text('מעבדה'));
      await tester.pumpAndSettle();

      expect(find.text('גלוקוז (mg/dL)'), findsOneWidget);
      expect(find.text('תפקוד כליות (eGFR) (mL/min)'), findsNothing);
      expect(find.text('מוצגים רק מדדים עם לפחות 2 בדיקות.'), findsOneWidget);
    });
  });
}