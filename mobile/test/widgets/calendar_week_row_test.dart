import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:vitalis/widgets/calendar_week_row.dart';
import 'package:vitalis/providers/meal_provider.dart';

void main() {
  group('CalendarWeekRow', () {
    final weekStart = DateTime(2026, 6, 28); // a Sunday
    final statuses = [
      DayStatus.trackedWithinBudget, // Sun
      DayStatus.trackedExceeded, // Mon
      DayStatus.untracked, // Tue
      DayStatus.trackedWithinBudget, // Wed
      DayStatus.untracked, // Thu
      DayStatus.trackedWithinBudget, // Fri
      DayStatus.future, // Sat
    ];

    testWidgets('renders 7 dots for Sun-Sat', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: CalendarWeekRow(
              weekStart: weekStart,
              selectedDay: weekStart,
              statuses: statuses,
              onDaySelected: (_) {},
            ),
          ),
        ),
      );

      expect(
        find.byKey(const ValueKey('calendar-dot-0')),
        findsOneWidget,
      );
      for (var i = 0; i < 7; i++) {
        expect(find.byKey(ValueKey('calendar-dot-$i')), findsOneWidget);
      }
    });

    testWidgets('highlights the currently selected day', (tester) async {
      final selected = weekStart.add(const Duration(days: 2));
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: CalendarWeekRow(
              weekStart: weekStart,
              selectedDay: selected,
              statuses: statuses,
              onDaySelected: (_) {},
            ),
          ),
        ),
      );

      final hasHighlighted = tester
          .widgetList<Container>(find.byType(Container))
          .any((c) =>
              c.decoration is BoxDecoration &&
              (c.decoration as BoxDecoration).border != null);
      expect(hasHighlighted, true);
    });

    testWidgets('shows correct color per DayStatus', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: CalendarWeekRow(
              weekStart: weekStart,
              selectedDay: weekStart,
              statuses: statuses,
              onDaySelected: (_) {},
            ),
          ),
        ),
      );

      final colors = tester
          .widgetList<Container>(find.byType(Container))
          .map((c) => c.decoration)
          .whereType<BoxDecoration>()
          .map((d) => d.color)
          .toList();

      expect(colors, contains(Colors.green));
      expect(colors, contains(Colors.red));
    });

    testWidgets('tapping a dot invokes onDaySelected callback with that date', (tester) async {
      DateTime? tapped;
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: CalendarWeekRow(
              weekStart: weekStart,
              selectedDay: weekStart,
              statuses: statuses,
              onDaySelected: (d) => tapped = d,
            ),
          ),
        ),
      );

      await tester.tap(find.byKey(const ValueKey('calendar-dot-2')));
      await tester.pump();

      expect(tapped, weekStart.add(const Duration(days: 2)));
    });

    testWidgets('tapping prev/next week arrow invokes callbacks', (tester) async {
      var prevTapped = false;
      var nextTapped = false;
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: CalendarWeekRow(
              weekStart: weekStart,
              selectedDay: weekStart,
              statuses: statuses,
              onDaySelected: (_) {},
              onPrevWeek: () => prevTapped = true,
              onNextWeek: () => nextTapped = true,
            ),
          ),
        ),
      );

      await tester.tap(find.byIcon(Icons.keyboard_double_arrow_right));
      await tester.tap(find.byIcon(Icons.keyboard_double_arrow_left));
      await tester.pump();

      expect(prevTapped, true);
      expect(nextTapped, true);
    });
  });
}
