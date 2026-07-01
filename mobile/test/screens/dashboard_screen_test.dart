import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:http/testing.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

import 'package:vitalis/screens/dashboard_screen.dart';
import 'package:vitalis/providers/meal_provider.dart';
import 'package:vitalis/providers/goals_provider.dart';
import 'package:vitalis/providers/summary_provider.dart';
import 'package:vitalis/providers/training_provider.dart';
import 'package:vitalis/services/api_client.dart';
import 'package:vitalis/widgets/weekly_balance_bar.dart';

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

  group('DashboardScreen', () {
    testWidgets('shows calories progress', (tester) async {
      await tester.pumpWidget(
        MultiProvider(
          providers: [
            ChangeNotifierProvider(create: (_) => MealProvider(client)),
            ChangeNotifierProvider(create: (_) => GoalsProvider(client)),
            ChangeNotifierProvider(create: (_) => SummaryProvider(client)),
            ChangeNotifierProvider(create: (_) => TrainingProvider(client)),
          ],
          child: const MaterialApp(home: DashboardScreen()),
        ),
      );

      expect(find.text('0'), findsOneWidget); // 0 calories
      expect(find.text('Vitalis'), findsOneWidget);
      expect(find.byType(LinearProgressIndicator), findsWidgets);
    });

    testWidgets('shows macro breakdown bars', (tester) async {
      await tester.pumpWidget(
        MultiProvider(
          providers: [
            ChangeNotifierProvider(create: (_) => MealProvider(client)),
            ChangeNotifierProvider(create: (_) => GoalsProvider(client)),
            ChangeNotifierProvider(create: (_) => SummaryProvider(client)),
            ChangeNotifierProvider(create: (_) => TrainingProvider(client)),
          ],
          child: const MaterialApp(home: DashboardScreen()),
        ),
      );

      expect(find.text('חלבון'), findsOneWidget);
      expect(find.text('פחמימות'), findsOneWidget);
      expect(find.text('שומן'), findsOneWidget);
    });

    testWidgets('displays weekly balance bar below daily calories card', (tester) async {
      final today = DateTime.now();
      final todayKey =
          '${today.year}-${today.month.toString().padLeft(2, '0')}-${today.day.toString().padLeft(2, '0')}';

      final mockClient = MockClient((req) async {
        if (req.url.path.contains('/v1/nutrition/day-overrides')) {
          return http.Response(jsonEncode({'overrides': []}), 200);
        }
        if (req.url.path.contains('/v1/goals')) {
          return http.Response(
            jsonEncode({
              'goal': {
                'date': todayKey,
                'calories_target': 2000,
                'protein_g_target': 150,
                'carbs_g_target': 200,
                'fat_g_target': 70,
                'set_by': 'agent',
              }
            }),
            200,
          );
        }
        if (req.url.path.contains('/v1/nutrition')) {
          return http.Response(
            jsonEncode({
              'meals': {
                todayKey: [
                  {
                    'food_name': 'food',
                    'calories': 2300,
                    'protein_g': 1,
                    'carbs_g': 1,
                    'fat_g': 1,
                    'source': 'history',
                    'timestamp': today.toIso8601String(),
                  }
                ]
              }
            }),
            200,
          );
        }
        return http.Response('', 404);
      });

      final localClient = ApiClient(
        baseUrl: 'http://test/api',
        apiKey: 'test-key',
        httpClient: mockClient,
      );

      await tester.pumpWidget(
        MultiProvider(
          providers: [
            ChangeNotifierProvider(create: (_) => MealProvider(localClient)),
            ChangeNotifierProvider(create: (_) => GoalsProvider(localClient)),
            ChangeNotifierProvider(create: (_) => SummaryProvider(localClient)),
            ChangeNotifierProvider(create: (_) => TrainingProvider(localClient)),
          ],
          child: const MaterialApp(home: DashboardScreen()),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.byType(WeeklyBalanceBar), findsOneWidget);
      expect(find.textContaining('+300'), findsOneWidget); // 2300 - 2000
      expect(find.textContaining('1/7 ימים'), findsOneWidget);
    });

    testWidgets('weekly balance bar reflects rollingWeekBalance from MealProvider', (tester) async {
      final mockClient = MockClient((req) async {
        if (req.url.path.contains('/v1/nutrition/day-overrides')) {
          return http.Response(jsonEncode({'overrides': []}), 200);
        }
        if (req.url.path.contains('/v1/goals')) {
          return http.Response(
            jsonEncode({
              'goal': {
                'date': '2026-04-04',
                'calories_target': 2000,
                'protein_g_target': 150,
                'carbs_g_target': 200,
                'fat_g_target': 70,
                'set_by': 'agent',
              }
            }),
            200,
          );
        }
        return http.Response(jsonEncode({'meals': {}}), 200);
      });

      final localClient = ApiClient(
        baseUrl: 'http://test/api',
        apiKey: 'test-key',
        httpClient: mockClient,
      );

      await tester.pumpWidget(
        MultiProvider(
          providers: [
            ChangeNotifierProvider(create: (_) => MealProvider(localClient)),
            ChangeNotifierProvider(create: (_) => GoalsProvider(localClient)),
            ChangeNotifierProvider(create: (_) => SummaryProvider(localClient)),
            ChangeNotifierProvider(create: (_) => TrainingProvider(localClient)),
          ],
          child: const MaterialApp(home: DashboardScreen()),
        ),
      );
      await tester.pumpAndSettle();

      // No meals logged in the window -> 0 tracked days, balance stays 0.
      expect(find.byType(WeeklyBalanceBar), findsOneWidget);
      expect(find.textContaining('0/7 ימים'), findsOneWidget);
    });
  });
}
