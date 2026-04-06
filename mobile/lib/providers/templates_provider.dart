import 'package:flutter/foundation.dart';

import '../models/meal_entry.dart';
import '../models/meal_template.dart';
import '../services/api_client.dart';

class TemplatesProvider extends ChangeNotifier {
  final ApiClient _api;

  List<MealTemplate> _templates = <MealTemplate>[];
  List<MealTemplate> get templates => List.unmodifiable(_templates);

  bool _loading = false;
  bool get loading => _loading;

  TemplatesProvider(this._api);

  Future<void> loadTemplates() async {
    _loading = true;
    notifyListeners();
    try {
      _templates = await _api.getTemplates();
    } finally {
      _loading = false;
      notifyListeners();
    }
  }

  Future<void> addTemplate(String name, List<MealEntry> meals, {String? notes}) async {
    final template = await _api.createTemplate(name, meals, notes: notes);
    _templates = List<MealTemplate>.from(_templates)..add(template);
    notifyListeners();
  }

  Future<void> removeTemplate(String id) async {
    await _api.deleteTemplate(id);
    _templates = _templates.where((item) => item.id != id).toList();
    notifyListeners();
  }
}