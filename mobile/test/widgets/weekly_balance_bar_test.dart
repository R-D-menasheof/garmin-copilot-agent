import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:vitalis/widgets/weekly_balance_bar.dart';

void main() {
  group('WeeklyBalanceBar', () {
    testWidgets('renders balance value and tracked-day count', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: WeeklyBalanceBar(balance: -200, trackedDays: 5),
          ),
        ),
      );

      expect(find.textContaining('-200'), findsOneWidget);
      expect(find.textContaining('5/7'), findsOneWidget);
    });

    testWidgets('shows green styling when balance is within budget (deficit or small surplus)', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: WeeklyBalanceBar(balance: 100, trackedDays: 7),
          ),
        ),
      );

      final text = tester.widget<Text>(find.textContaining('קק"ל'));
      expect(text.style?.color, Colors.green);
    });

    testWidgets('shows warning styling when balance exceeds budget significantly', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: WeeklyBalanceBar(balance: 900, trackedDays: 7),
          ),
        ),
      );

      final text = tester.widget<Text>(find.textContaining('קק"ל'));
      expect(text.style?.color, Colors.orange);
    });

    testWidgets('hides gracefully when balance is null', (tester) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(
            body: WeeklyBalanceBar(balance: null, trackedDays: 0),
          ),
        ),
      );

      expect(find.byType(WeeklyBalanceBar), findsOneWidget);
      expect(find.textContaining('קק"ל'), findsNothing);
    });
  });
}
