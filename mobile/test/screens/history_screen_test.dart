import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:http/testing.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

import 'package:vitalis/screens/history_screen.dart';
import 'package:vitalis/providers/meal_provider.dart';
import 'package:vitalis/services/api_client.dart';

String _dateKey(DateTime day) =>
  '${day.year}-${day.month.toString().padLeft(2, '0')}-${day.day.toString().padLeft(2, '0')}';

void main() {
  late ApiClient client;

  setUp(() {
    final mockClient = MockClient((req) async {
      return http.Response(jsonEncode({'meals': {}}), 200);
    });
    client = ApiClient(
      baseUrl: 'http://test/api',
      apiKey: 'test-key',
      httpClient: mockClient,
    );
  });

  group('HistoryScreen', () {
    testWidgets('shows date navigation', (tester) async {
      await tester.pumpWidget(
        ChangeNotifierProvider(
          create: (_) => MealProvider(client),
          child: const MaterialApp(home: HistoryScreen()),
        ),
      );
      await tester.pumpAndSettle();

      // Should show "today" label and nav arrows
      expect(find.byIcon(Icons.chevron_right), findsOneWidget);
      expect(find.byIcon(Icons.chevron_left), findsOneWidget);
    });

    testWidgets('shows empty state message', (tester) async {
      await tester.pumpWidget(
        ChangeNotifierProvider(
          create: (_) => MealProvider(client),
          child: const MaterialApp(home: HistoryScreen()),
        ),
      );
      await tester.pumpAndSettle();

      // No meals loaded, should show empty state
      expect(find.byType(ListView), findsNothing);
    });

    testWidgets('shows today meals after provider loads them', (tester) async {
      final today = DateTime.now();
      final mockClient = MockClient((req) async {
        return http.Response(
          jsonEncode({
            'meals': {
              _dateKey(today): [
                {
                  'food_name': 'banana',
                  'calories': 89,
                  'protein_g': 1.1,
                  'carbs_g': 22.8,
                  'fat_g': 0.3,
                  'source': 'history',
                  'timestamp': today.toIso8601String(),
                }
              ]
            }
          }),
          200,
        );
      });
      final provider = MealProvider(
        ApiClient(
          baseUrl: 'http://test/api',
          apiKey: 'test-key',
          httpClient: mockClient,
        ),
      );

      await tester.pumpWidget(
        ChangeNotifierProvider.value(
          value: provider,
          child: const MaterialApp(home: HistoryScreen()),
        ),
      );

      await provider.loadToday();
      await tester.pumpAndSettle();

      expect(find.text('banana'), findsOneWidget);
    });
  });
}
