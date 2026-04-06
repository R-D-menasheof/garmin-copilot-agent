import 'package:flutter_test/flutter_test.dart';

import 'package:vitalis/providers/goals_provider.dart';
import 'package:vitalis/models/nutrition_goal.dart';
import 'package:vitalis/services/api_client.dart';
import 'package:http/testing.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

void main() {
  group('GoalsProvider', () {
    test('compliancePct calculates correctly', () {
      final mockClient = MockClient((req) async => http.Response('', 404));
      final client = ApiClient(
        baseUrl: 'http://test/api',
        apiKey: 'test-key',
        httpClient: mockClient,
      );

      final provider = GoalsProvider(client);

      // No goal set
      expect(provider.compliancePct(1000), isNull);
    });

    test('compliancePct returns percentage of target', () {
      final mockClient = MockClient((req) async {
        return http.Response(
          jsonEncode({
            'goal': {
              'date': '2026-04-04',
              'calories_target': 2200,
              'protein_g_target': 180,
              'carbs_g_target': 250,
              'fat_g_target': 70,
              'set_by': 'agent',
            }
          }),
          200,
        );
      });

      final client = ApiClient(
        baseUrl: 'http://test/api',
        apiKey: 'test-key',
        httpClient: mockClient,
      );

      final provider = GoalsProvider(client);

      // Manually simulate loaded goal
      provider.loadGoals().then((_) {
        final pct = provider.compliancePct(1100);
        expect(pct, closeTo(50.0, 1.0));
      });
    });
  });
}
