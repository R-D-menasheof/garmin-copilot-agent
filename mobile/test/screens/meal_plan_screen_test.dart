import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:provider/provider.dart';

import 'package:vitalis/providers/plan_provider.dart';
import 'package:vitalis/providers/templates_provider.dart';
import 'package:vitalis/screens/meal_plan_screen.dart';
import 'package:vitalis/services/api_client.dart';

void main() {
  group('MealPlanScreen', () {
    testWidgets('shows planned templates, notes, and grocery preview', (tester) async {
      final mockClient = MockClient((req) async {
        if (req.url.path.contains('/v1/templates')) {
          return http.Response(
            jsonEncode({
              'templates': [
                {
                  'id': 'template-1',
                  'name': 'Breakfast',
                  'notes': 'Default breakfast',
                  'created_at': '2026-04-04T09:00:00',
                  'meals': [
                    {
                      'food_name': 'toast',
                      'calories': 120,
                      'protein_g': 4.0,
                      'carbs_g': 20.0,
                      'fat_g': 2.0,
                      'source': 'history',
                      'timestamp': '2026-04-04T08:00:00',
                    }
                  ]
                },
                {
                  'id': 'template-2',
                  'name': 'Snack',
                  'notes': null,
                  'created_at': '2026-04-04T10:00:00',
                  'meals': [
                    {
                      'food_name': 'banana',
                      'calories': 89,
                      'protein_g': 1.1,
                      'carbs_g': 22.8,
                      'fat_g': 0.3,
                      'source': 'history',
                      'timestamp': '2026-04-04T10:00:00',
                    }
                  ]
                }
              ]
            }),
            200,
          );
        }

        if (req.url.path.contains('/v1/plan')) {
          return http.Response(
            jsonEncode({
              'plan': {
                'date': '2026-04-04',
                'template_ids': ['template-1'],
                'notes': 'Training day',
                'created_at': '2026-04-03T20:00:00',
                'updated_at': '2026-04-04T06:00:00',
              }
            }),
            200,
          );
        }

        return http.Response('{}', 200);
      });

      final client = ApiClient(
        baseUrl: 'http://test/api',
        apiKey: 'test-key',
        httpClient: mockClient,
      );

      await tester.pumpWidget(
        MultiProvider(
          providers: [
            ChangeNotifierProvider(create: (_) => TemplatesProvider(client)),
            ChangeNotifierProvider(create: (_) => PlanProvider(client)),
          ],
          child: MaterialApp(
            home: MealPlanScreen(initialDate: DateTime(2026, 4, 4)),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('תכנון יום'), findsOneWidget);
      expect(find.text('Breakfast'), findsOneWidget);
      expect(find.text('Snack'), findsOneWidget);
      expect(find.text('Training day'), findsOneWidget);
      await tester.drag(find.byType(Scrollable).first, const Offset(0, -600));
      await tester.pumpAndSettle();
      expect(find.text('toast x1'), findsOneWidget);
    });
  });
}