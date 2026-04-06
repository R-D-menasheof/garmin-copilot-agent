import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:vitalis/models/meal_entry.dart';
import 'package:vitalis/models/nutrition_source.dart';
import 'package:vitalis/providers/favorites_provider.dart';
import 'package:vitalis/services/api_client.dart';

void main() {
  group('FavoritesProvider', () {
    test('loadFavorites stores favorites from the API', () async {
      final mockClient = MockClient((req) async {
        return http.Response(
          jsonEncode({
            'favorites': [
              {
                'id': 'favorite-1',
                'label': 'Morning toast',
                'created_at': '2026-04-04T09:00:00',
                'meal': {
                  'food_name': 'toast',
                  'calories': 120,
                  'protein_g': 4.0,
                  'carbs_g': 20.0,
                  'fat_g': 2.0,
                  'source': 'history',
                  'timestamp': '2026-04-04T08:00:00',
                }
              }
            ]
          }),
          200,
        );
      });

      final provider = FavoritesProvider(
        ApiClient(
          baseUrl: 'http://test/api',
          apiKey: 'test-key',
          httpClient: mockClient,
        ),
      );

      await provider.loadFavorites();

      expect(provider.favorites, hasLength(1));
      expect(provider.favorites.single.meal.foodName, 'toast');
    });

    test('addFavoriteFromMeal saves and appends a new favorite', () async {
      final mockClient = MockClient((req) async {
        if (req.method == 'POST') {
          final body = jsonDecode(req.body) as Map<String, dynamic>;
          return http.Response(
            jsonEncode({
              'favorite': {
                'id': 'favorite-1',
                'label': body['label'],
                'created_at': '2026-04-04T09:00:00',
                'meal': body['meal'],
              }
            }),
            201,
          );
        }
        return http.Response(jsonEncode({'favorites': []}), 200);
      });

      final provider = FavoritesProvider(
        ApiClient(
          baseUrl: 'http://test/api',
          apiKey: 'test-key',
          httpClient: mockClient,
        ),
      );

      await provider.addFavoriteFromMeal(
        MealEntry(
          foodName: 'toast',
          calories: 120,
          proteinG: 4.0,
          carbsG: 20.0,
          fatG: 2.0,
          source: NutritionSource.history,
          timestamp: DateTime(2026, 4, 4, 8, 0),
        ),
        label: 'Morning toast',
      );

      expect(provider.favorites, hasLength(1));
      expect(provider.favorites.single.label, 'Morning toast');
    });
  });
}