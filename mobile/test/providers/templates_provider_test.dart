import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:vitalis/models/meal_entry.dart';
import 'package:vitalis/models/nutrition_source.dart';
import 'package:vitalis/providers/templates_provider.dart';
import 'package:vitalis/services/api_client.dart';

void main() {
  group('TemplatesProvider', () {
    test('loadTemplates stores templates from the API', () async {
      final mockClient = MockClient((req) async {
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
              }
            ]
          }),
          200,
        );
      });

      final provider = TemplatesProvider(
        ApiClient(
          baseUrl: 'http://test/api',
          apiKey: 'test-key',
          httpClient: mockClient,
        ),
      );

      await provider.loadTemplates();

      expect(provider.templates, hasLength(1));
      expect(provider.templates.single.name, 'Breakfast');
    });

    test('addTemplate saves and appends a new template', () async {
      final mockClient = MockClient((req) async {
        if (req.method == 'POST') {
          final body = jsonDecode(req.body) as Map<String, dynamic>;
          return http.Response(
            jsonEncode({
              'template': {
                'id': 'template-1',
                'name': body['name'],
                'notes': body['notes'],
                'created_at': '2026-04-04T09:00:00',
                'meals': body['meals'],
              }
            }),
            201,
          );
        }
        return http.Response(jsonEncode({'templates': []}), 200);
      });

      final provider = TemplatesProvider(
        ApiClient(
          baseUrl: 'http://test/api',
          apiKey: 'test-key',
          httpClient: mockClient,
        ),
      );

      await provider.addTemplate(
        'Breakfast',
        [
          MealEntry(
            foodName: 'toast',
            calories: 120,
            proteinG: 4.0,
            carbsG: 20.0,
            fatG: 2.0,
            source: NutritionSource.history,
            timestamp: DateTime(2026, 4, 4, 8, 0),
          ),
        ],
        notes: 'Default breakfast',
      );

      expect(provider.templates, hasLength(1));
      expect(provider.templates.single.name, 'Breakfast');
    });
  });
}