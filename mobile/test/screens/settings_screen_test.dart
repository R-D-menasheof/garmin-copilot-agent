import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';

import 'package:vitalis/screens/settings_screen.dart';
import 'package:vitalis/providers/biometrics_provider.dart';
import 'package:vitalis/services/health_connect.dart';

void main() {
  group('SettingsScreen', () {
    testWidgets('shows API key field', (tester) async {
      await tester.pumpWidget(
        ChangeNotifierProvider(
          create: (_) => BiometricsProvider(HealthConnectService()),
          child: const MaterialApp(home: SettingsScreen()),
        ),
      );

      expect(find.text('API Key'), findsOneWidget);
      expect(find.text('הגדרות'), findsOneWidget);
    });
  });
}
