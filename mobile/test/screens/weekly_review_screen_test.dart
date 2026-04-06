import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:provider/provider.dart';

import 'package:vitalis/providers/summary_provider.dart';
import 'package:vitalis/screens/weekly_review_screen.dart';
import 'package:vitalis/services/api_client.dart';

void main() {
  group('WeeklyReviewScreen', () {
    testWidgets('renders summary history cards', (tester) async {
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

      await tester.pumpWidget(
        ChangeNotifierProvider.value(
          value: provider,
          child: const MaterialApp(home: WeeklyReviewScreen()),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('סקירה שבועית'), findsOneWidget);
      expect(find.text('Average steps increased'), findsOneWidget);
      expect(find.text('Keep walking'), findsOneWidget);
    });
  });
}