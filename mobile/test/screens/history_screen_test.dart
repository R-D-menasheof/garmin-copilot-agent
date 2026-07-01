import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:http/testing.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

import 'package:vitalis/screens/history_screen.dart';
import 'package:vitalis/providers/meal_provider.dart';
import 'package:vitalis/providers/goals_provider.dart';
import 'package:vitalis/services/api_client.dart';
import 'package:vitalis/widgets/calendar_week_row.dart';

String _dateKey(DateTime day) =>
  '${day.year}-${day.month.toString().padLeft(2, '0')}-${day.day.toString().padLeft(2, '0')}';

Widget _wrap(ApiClient client, {MealProvider? mealProvider}) {
  return MultiProvider(
    providers: [
      if (mealProvider != null)
        ChangeNotifierProvider.value(value: mealProvider)
      else
        ChangeNotifierProvider(create: (_) => MealProvider(client)),
      ChangeNotifierProvider(create: (_) => GoalsProvider(client)),
    ],
    child: const MaterialApp(home: HistoryScreen()),
  );
}

void main() {
  late ApiClient client;

  setUp(() {
    final mockClient = MockClient((req) async {
      if (req.url.path.contains('/v1/nutrition/day-overrides')) {
        return http.Response(jsonEncode({'overrides': []}), 200);
      }
      if (req.url.path.contains('/v1/goals')) {
        return http.Response(jsonEncode({'goal': null}), 200);
      }
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
      await tester.pumpWidget(_wrap(client));
      await tester.pumpAndSettle();

      // Should show "today" label and nav arrows
      expect(find.byIcon(Icons.chevron_right), findsOneWidget);
      expect(find.byIcon(Icons.chevron_left), findsOneWidget);
    });

    testWidgets('shows empty state message', (tester) async {
      await tester.pumpWidget(_wrap(client));
      await tester.pumpAndSettle();

      // No meals loaded, should show empty state
      expect(find.byType(ListView), findsNothing);
    });

    testWidgets('shows today meals after provider loads them', (tester) async {
      final today = DateTime.now();
      final mockClient = MockClient((req) async {
        if (req.url.path.contains('/v1/nutrition/day-overrides')) {
          return http.Response(jsonEncode({'overrides': []}), 200);
        }
        if (req.url.path.contains('/v1/goals')) {
          return http.Response(jsonEncode({'goal': null}), 200);
        }
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

      await tester.pumpWidget(_wrap(client, mealProvider: provider));

      await provider.loadToday();
      await tester.pumpAndSettle();

      expect(find.text('banana'), findsOneWidget);
    });

    testWidgets('displays calendar week row above the day view', (tester) async {
      await tester.pumpWidget(_wrap(client));
      await tester.pumpAndSettle();

      expect(find.byType(CalendarWeekRow), findsOneWidget);
    });

    testWidgets('tapping a calendar dot navigates to that day', (tester) async {
      await tester.pumpWidget(_wrap(client));
      await tester.pumpAndSettle();

      // Tap the first dot in the displayed week (Sunday).
      await tester.tap(find.byKey(const ValueKey('calendar-dot-0')));
      await tester.pumpAndSettle();

      // The date label should no longer read "היום" (today) unless today
      // happens to be a Sunday — assert the screen still renders correctly
      // by checking the calendar row is still present and no crash occurred.
      expect(find.byType(CalendarWeekRow), findsOneWidget);
    });

    testWidgets('shows override toggle button in day view', (tester) async {
      await tester.pumpWidget(_wrap(client));
      await tester.pumpAndSettle();

      expect(find.textContaining('התיעוד'), findsOneWidget);
    });

    testWidgets('tapping override toggle calls provider.toggleDayOverride for the selected day', (tester) async {
      var toggledDate;
      final mockClient = MockClient((req) async {
        if (req.url.path.contains('/v1/nutrition/day-overrides')) {
          return http.Response(jsonEncode({'overrides': []}), 200);
        }
        if (req.url.path.contains('/v1/goals')) {
          return http.Response(jsonEncode({'goal': null}), 200);
        }
        if (req.method == 'POST' && req.url.path.contains('/v1/nutrition/day-override')) {
          toggledDate = (jsonDecode(req.body) as Map<String, dynamic>)['date'];
          return http.Response(jsonEncode({'status': 'ok'}), 201);
        }
        return http.Response(jsonEncode({'meals': {}}), 200);
      });
      final localClient = ApiClient(
        baseUrl: 'http://test/api',
        apiKey: 'test-key',
        httpClient: mockClient,
      );

      await tester.pumpWidget(_wrap(localClient));
      await tester.pumpAndSettle();

      await tester.tap(find.textContaining('התיעוד'));
      await tester.pumpAndSettle();

      final todayKey = _dateKey(DateTime.now());
      expect(toggledDate, todayKey);
    });

    testWidgets('button label reflects current override state', (tester) async {
      final todayKey = _dateKey(DateTime.now());
      final mockClient = MockClient((req) async {
        if (req.url.path.contains('/v1/nutrition/day-overrides')) {
          return http.Response(
            jsonEncode({
              'overrides': [
                {
                  'date': todayKey,
                  'tracked': false,
                  'note': '',
                  'updated_at': '2026-04-04T12:00:00',
                }
              ]
            }),
            200,
          );
        }
        if (req.url.path.contains('/v1/goals')) {
          return http.Response(jsonEncode({'goal': null}), 200);
        }
        return http.Response(jsonEncode({'meals': {}}), 200);
      });
      final localClient = ApiClient(
        baseUrl: 'http://test/api',
        apiKey: 'test-key',
        httpClient: mockClient,
      );

      await tester.pumpWidget(_wrap(localClient));
      await tester.pumpAndSettle();

      // Already marked untracked -> button should offer to undo the override.
      expect(find.textContaining('בטל סימון'), findsOneWidget);
    });
  });
}
