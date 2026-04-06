import 'package:flutter/foundation.dart';

import '../models/analysis_summary.dart';
import '../services/api_client.dart';

class SummaryProvider extends ChangeNotifier {
  final ApiClient _api;

  AnalysisSummary? _latestSummary;
  AnalysisSummary? get latestSummary => _latestSummary;
  List<AnalysisSummary> _summaryHistory = <AnalysisSummary>[];
  List<AnalysisSummary> get summaryHistory => List.unmodifiable(_summaryHistory);

  bool _loading = false;
  bool get loading => _loading;

  String? _error;
  String? get error => _error;

  SummaryProvider(this._api);

  Future<void> loadLatestSummary() async {
    _loading = true;
    _error = null;
    notifyListeners();
    try {
      _latestSummary = await _api.getLatestSummary();
    } catch (error) {
      _error = error.toString();
    } finally {
      _loading = false;
      notifyListeners();
    }
  }

  Future<void> loadSummaryHistory({int limit = 4}) async {
    _loading = true;
    _error = null;
    notifyListeners();
    try {
      _summaryHistory = await _api.getSummaryHistory(limit: limit);
    } catch (error) {
      _error = error.toString();
    } finally {
      _loading = false;
      notifyListeners();
    }
  }
}