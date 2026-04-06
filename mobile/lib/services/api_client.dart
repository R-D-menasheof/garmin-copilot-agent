import 'dart:convert';
import 'dart:typed_data';
import 'package:http/http.dart' as http;

import '../models/analysis_summary.dart';
import '../models/favorite_meal.dart';
import '../models/meal_entry.dart';
import '../models/meal_template.dart';
import '../models/plan_day.dart';
import '../models/nutrition_goal.dart';
import '../models/biometrics_record.dart';

/// HTTP client for the Vitalis Azure Functions API.
class ApiClient {
  final String baseUrl;
  final String apiKey;
  final http.Client _httpClient;

  ApiClient({
    required this.baseUrl,
    required this.apiKey,
    http.Client? httpClient,
  }) : _httpClient = httpClient ?? http.Client();

  Map<String, String> get _headers => {
        'x-api-key': apiKey,
        'Content-Type': 'application/json',
      };

  // ── Read API ─────────────────────────────────────────────

  Future<Map<String, List<MealEntry>>> getNutrition(
    DateTime from,
    DateTime to,
  ) async {
    final uri = Uri.parse('$baseUrl/v1/nutrition').replace(queryParameters: {
      'from': _formatDate(from),
      'to': _formatDate(to),
    });
    final resp = await _httpClient.get(uri, headers: _headers);
    _checkResponse(resp);
    final body = jsonDecode(resp.body) as Map<String, dynamic>;
    final meals = body['meals'] as Map<String, dynamic>;
    return meals.map((date, list) => MapEntry(
          date,
          (list as List).map((m) => MealEntry.fromJson(m)).toList(),
        ));
  }

  Future<NutritionGoal?> getGoals() async {
    final uri = Uri.parse('$baseUrl/v1/goals');
    final resp = await _httpClient.get(uri, headers: _headers);
    if (resp.statusCode == 404) return null;
    _checkResponse(resp);
    final body = jsonDecode(resp.body) as Map<String, dynamic>;
    return NutritionGoal.fromJson(body['goal']);
  }

  Future<List<MealEntry>> getRecents({int limit = 10}) async {
    final uri = Uri.parse('$baseUrl/v1/recents').replace(queryParameters: {
      'limit': '$limit',
    });
    final resp = await _httpClient.get(uri, headers: _headers);
    _checkResponse(resp);
    final body = jsonDecode(resp.body) as Map<String, dynamic>;
    final recents = body['recents'];
    if (recents == null) {
      return <MealEntry>[];
    }
    return (recents as List)
        .map((m) => MealEntry.fromJson(m as Map<String, dynamic>))
        .toList();
  }

  Future<AnalysisSummary?> getLatestSummary() async {
    final uri = Uri.parse('$baseUrl/v1/summary/latest');
    final resp = await _httpClient.get(uri, headers: _headers);
    _checkResponse(resp);
    final body = jsonDecode(resp.body) as Map<String, dynamic>;
    final summary = body['summary'];
    if (summary == null) {
      return null;
    }
    return AnalysisSummary.fromJson(summary as Map<String, dynamic>);
  }

  Future<List<AnalysisSummary>> getSummaryHistory({int limit = 4}) async {
    final uri = Uri.parse('$baseUrl/v1/summary/history').replace(queryParameters: {
      'limit': '$limit',
    });
    final resp = await _httpClient.get(uri, headers: _headers);
    _checkResponse(resp);
    final body = jsonDecode(resp.body) as Map<String, dynamic>;
    final summaries = body['summaries'];
    if (summaries == null) {
      return <AnalysisSummary>[];
    }
    return (summaries as List)
        .map((item) => AnalysisSummary.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  Future<List<FavoriteMeal>> getFavorites() async {
    final uri = Uri.parse('$baseUrl/v1/favorites');
    final resp = await _httpClient.get(uri, headers: _headers);
    _checkResponse(resp);
    final body = jsonDecode(resp.body) as Map<String, dynamic>;
    final favorites = body['favorites'];
    if (favorites == null) {
      return <FavoriteMeal>[];
    }
    return (favorites as List)
        .map((item) => FavoriteMeal.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  Future<List<MealTemplate>> getTemplates() async {
    final uri = Uri.parse('$baseUrl/v1/templates');
    final resp = await _httpClient.get(uri, headers: _headers);
    _checkResponse(resp);
    final body = jsonDecode(resp.body) as Map<String, dynamic>;
    final templates = body['templates'];
    if (templates == null) {
      return <MealTemplate>[];
    }
    return (templates as List)
        .map((item) => MealTemplate.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  Future<PlanDay?> getPlanDay(DateTime day) async {
    final uri = Uri.parse('$baseUrl/v1/plan').replace(queryParameters: {
      'date': _formatDate(day),
    });
    final resp = await _httpClient.get(uri, headers: _headers);
    _checkResponse(resp);
    final body = jsonDecode(resp.body) as Map<String, dynamic>;
    final plan = body['plan'];
    if (plan == null) {
      return null;
    }
    return PlanDay.fromJson(plan as Map<String, dynamic>);
  }

  // ── Write API ────────────────────────────────────────────

  Future<MealEntry> postMeal(MealEntry meal) async {
    final uri = Uri.parse('$baseUrl/v1/meals');
    final resp = await _httpClient.post(
      uri,
      headers: _headers,
      body: jsonEncode(meal.toJson()),
    );
    _checkResponse(resp);
    final body = jsonDecode(resp.body) as Map<String, dynamic>;
    return MealEntry.fromJson(body['meal']);
  }

  Future<void> postGoals(NutritionGoal goal) async {
    final uri = Uri.parse('$baseUrl/v1/goals');
    final resp = await _httpClient.post(
      uri,
      headers: _headers,
      body: jsonEncode(goal.toJson()),
    );
    _checkResponse(resp);
  }

  Future<void> postBiometrics(BiometricsRecord record) async {
    final uri = Uri.parse('$baseUrl/v1/biometrics');
    final resp = await _httpClient.post(
      uri,
      headers: _headers,
      body: jsonEncode(record.toJson()),
    );
    _checkResponse(resp);
  }

  Future<void> putMeals(DateTime day, List<MealEntry> meals) async {
    final uri = Uri.parse('$baseUrl/v1/meals');
    final resp = await _httpClient.put(
      uri,
      headers: _headers,
      body: jsonEncode({
        'date': _formatDate(day),
        'meals': meals.map((meal) => meal.toJson()).toList(),
      }),
    );
    _checkResponse(resp);
  }

  // ── Ingestion API ────────────────────────────────────────

  Future<List<MealEntry>> analyzeImage(Uint8List imageBytes) async {
    final uri = Uri.parse('$baseUrl/v1/analyze-image');
    final resp = await _httpClient.post(
      uri,
      headers: _headers,
      body: jsonEncode({'image': base64Encode(imageBytes)}),
    );
    _checkResponse(resp);
    final body = jsonDecode(resp.body) as Map<String, dynamic>;
    return (body['meals'] as List)
        .map((m) => MealEntry.fromJson(m))
        .toList();
  }

  Future<List<MealEntry>> analyzeText(String text) async {
    final uri = Uri.parse('$baseUrl/v1/analyze-text');
    final resp = await _httpClient.post(
      uri,
      headers: _headers,
      body: jsonEncode({'text': text}),
    );
    _checkResponse(resp);
    final body = jsonDecode(resp.body) as Map<String, dynamic>;
    return (body['meals'] as List)
        .map((m) => MealEntry.fromJson(m))
        .toList();
  }

  Future<List<MealEntry>> lookupBarcode(String barcode) async {
    final uri = Uri.parse('$baseUrl/v1/barcode');
    final resp = await _httpClient.post(
      uri,
      headers: _headers,
      body: jsonEncode({'barcode': barcode}),
    );
    _checkResponse(resp);
    final body = jsonDecode(resp.body) as Map<String, dynamic>;
    return (body['meals'] as List)
        .map((m) => MealEntry.fromJson(m as Map<String, dynamic>))
        .toList();
  }

  Future<FavoriteMeal> createFavorite(MealEntry meal, {String? label}) async {
    final uri = Uri.parse('$baseUrl/v1/favorites');
    final resp = await _httpClient.post(
      uri,
      headers: _headers,
      body: jsonEncode({
        'meal': meal.toJson(),
        if (label != null) 'label': label,
      }),
    );
    _checkResponse(resp);
    final body = jsonDecode(resp.body) as Map<String, dynamic>;
    return FavoriteMeal.fromJson(body['favorite'] as Map<String, dynamic>);
  }

  Future<void> deleteFavorite(String id) async {
    final uri = Uri.parse('$baseUrl/v1/favorites').replace(queryParameters: {'id': id});
    final resp = await _httpClient.delete(uri, headers: _headers);
    _checkResponse(resp);
  }

  Future<MealTemplate> createTemplate(
    String name,
    List<MealEntry> meals, {
    String? notes,
  }) async {
    final uri = Uri.parse('$baseUrl/v1/templates');
    final resp = await _httpClient.post(
      uri,
      headers: _headers,
      body: jsonEncode({
        'name': name,
        'meals': meals.map((meal) => meal.toJson()).toList(),
        if (notes != null) 'notes': notes,
      }),
    );
    _checkResponse(resp);
    final body = jsonDecode(resp.body) as Map<String, dynamic>;
    return MealTemplate.fromJson(body['template'] as Map<String, dynamic>);
  }

  Future<void> deleteTemplate(String id) async {
    final uri = Uri.parse('$baseUrl/v1/templates').replace(queryParameters: {'id': id});
    final resp = await _httpClient.delete(uri, headers: _headers);
    _checkResponse(resp);
  }

  Future<PlanDay> savePlanDay(
    DateTime day, {
    required List<String> templateIds,
    String? notes,
  }) async {
    final uri = Uri.parse('$baseUrl/v1/plan');
    final resp = await _httpClient.post(
      uri,
      headers: _headers,
      body: jsonEncode({
        'date': _formatDate(day),
        'template_ids': templateIds,
        if (notes != null) 'notes': notes,
      }),
    );
    _checkResponse(resp);
    final body = jsonDecode(resp.body) as Map<String, dynamic>;
    return PlanDay.fromJson(body['plan'] as Map<String, dynamic>);
  }

  // ── Helpers ──────────────────────────────────────────────

  String _formatDate(DateTime dt) =>
      '${dt.year}-${dt.month.toString().padLeft(2, '0')}-${dt.day.toString().padLeft(2, '0')}';

  void _checkResponse(http.Response resp) {
    if (resp.statusCode >= 400) {
      throw ApiException(resp.statusCode, resp.body);
    }
  }
}

class ApiException implements Exception {
  final int statusCode;
  final String body;
  const ApiException(this.statusCode, this.body);

  @override
  String toString() => 'ApiException($statusCode): $body';
}
