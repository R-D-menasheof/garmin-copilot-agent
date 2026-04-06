import 'package:flutter/foundation.dart';

import '../models/favorite_meal.dart';
import '../models/meal_entry.dart';
import '../services/api_client.dart';

class FavoritesProvider extends ChangeNotifier {
  final ApiClient _api;

  List<FavoriteMeal> _favorites = <FavoriteMeal>[];
  List<FavoriteMeal> get favorites => List.unmodifiable(_favorites);

  bool _loading = false;
  bool get loading => _loading;

  FavoritesProvider(this._api);

  Future<void> loadFavorites() async {
    _loading = true;
    notifyListeners();
    try {
      _favorites = await _api.getFavorites();
    } finally {
      _loading = false;
      notifyListeners();
    }
  }

  Future<void> addFavoriteFromMeal(MealEntry meal, {String? label}) async {
    final favorite = await _api.createFavorite(meal, label: label);
    _favorites = List<FavoriteMeal>.from(_favorites)..add(favorite);
    notifyListeners();
  }

  Future<void> removeFavorite(String id) async {
    await _api.deleteFavorite(id);
    _favorites = _favorites.where((item) => item.id != id).toList();
    notifyListeners();
  }
}