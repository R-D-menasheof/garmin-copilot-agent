import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:provider/provider.dart';

import 'package:vitalis/screens/settings_screen.dart';
import 'package:vitalis/providers/auth_provider.dart';
import 'package:vitalis/providers/biometrics_provider.dart';
import 'package:vitalis/services/api_client.dart';
import 'package:vitalis/services/auth_service.dart';
import 'package:vitalis/services/health_connect.dart';

/// Minimal AuthService fake so AuthProvider can be built in the widget tree.
class _FakeAuthService implements AuthService {
  @override
  Future<String?> signIn() async => null;

  @override
  Future<String?> restoreSession() async => null;

  @override
  Future<void> signOut() async {}
}

void main() {
  group('SettingsScreen', () {
    testWidgets('shows API key field', (tester) async {
      final api = ApiClient(
        baseUrl: 'http://test/api',
        apiKey: 'k',
        httpClient: MockClient((req) async => http.Response('{}', 200)),
      );

      await tester.pumpWidget(
        MultiProvider(
          providers: [
            ChangeNotifierProvider(
              create: (_) => BiometricsProvider(HealthConnectService()),
            ),
            ChangeNotifierProvider(
              create: (_) => AuthProvider(api, _FakeAuthService()),
            ),
          ],
          child: const MaterialApp(home: SettingsScreen()),
        ),
      );

      expect(find.text('API Key'), findsOneWidget);
      expect(find.text('הגדרות'), findsOneWidget);
    });
  });
}
