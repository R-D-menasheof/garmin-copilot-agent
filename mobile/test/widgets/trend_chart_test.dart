import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:vitalis/widgets/trend_chart.dart';

void main() {
  group('TrendChart', () {
    testWidgets('renders chart with data points', (tester) async {
      final data = [
        (DateTime(2026, 3, 28), 65.0),
        (DateTime(2026, 4, 4), 64.0),
      ];

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: TrendChart(
              title: 'RHR',
              unit: 'bpm',
              color: Colors.red,
              data: data,
            ),
          ),
        ),
      );

      expect(find.text('RHR (bpm)'), findsOneWidget);
    });

    testWidgets('renders bottom axis labels with month and year when configured', (tester) async {
      final data = [
        (DateTime(2020, 2, 26), 104.0),
        (DateTime(2022, 9, 19), 83.2),
      ];

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: TrendChart(
              title: 'LDL',
              unit: 'mg/dL',
              color: Colors.red,
              data: data,
              axisDateFormat: 'MM/yyyy',
            ),
          ),
        ),
      );

      expect(find.text('02/2020'), findsOneWidget);
      expect(find.text('09/2022'), findsOneWidget);
    });

    testWidgets('defaults to day/month axis labels', (tester) async {
      final data = [
        (DateTime(2026, 3, 28), 65.0),
        (DateTime(2026, 4, 4), 64.0),
      ];

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: TrendChart(
              title: 'RHR',
              unit: 'bpm',
              color: Colors.red,
              data: data,
            ),
          ),
        ),
      );

      expect(find.text('28/3'), findsOneWidget);
      expect(find.text('4/4'), findsOneWidget);
    });

    testWidgets('shows selected point full date label', (tester) async {
      final data = [
        (DateTime(2020, 2, 26), 104.0),
        (DateTime(2022, 9, 19), 83.2),
      ];

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: TrendChart(
              title: 'LDL',
              unit: 'mg/dL',
              color: Colors.red,
              data: data,
              axisDateFormat: 'MM/yyyy',
            ),
          ),
        ),
      );

      expect(find.text('בדיקה נבחרת: 19/09/2022'), findsOneWidget);
    });

    testWidgets('shows empty state when no data', (tester) async {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: TrendChart(
              title: 'Weight',
              unit: 'kg',
              color: Colors.blue,
              data: const [],
            ),
          ),
        ),
      );

      expect(find.text('אין נתונים'), findsOneWidget);
    });
  });
}
