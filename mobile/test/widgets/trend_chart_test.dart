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
