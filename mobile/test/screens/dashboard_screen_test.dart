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
import 'package:vitalis/services/api_client.dart';

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
          ],
          child: const MaterialApp(home: DashboardScreen()),
        ),
      );

      expect(find.text('חלבון'), findsOneWidget);
      expect(find.text('פחמימות'), findsOneWidget);
      expect(find.text('שומן'), findsOneWidget);
    });
  });
}
