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

  /// Key metrics to extract for trend charts.
  static const _trendMetrics = [
    'avg_resting_hr',
    'avg_hrv_nightly',
    'avg_sleep_hours',
    'weight_kg',
    'avg_daily_steps',
    'avg_body_battery_peak',
  ];

  /// Extract time-series data from summary history for trend charts.
  ///
  /// Returns a map of metric name → list of (date, value) tuples,
  /// sorted by date ascending (oldest first).
  Map<String, List<(DateTime, double)>> extractTrendData() {
    final result = <String, List<(DateTime, double)>>{};
    for (final metric in _trendMetrics) {
      result[metric] = [];
    }

    // Sort summaries oldest first
    final sorted = [..._summaryHistory]
      ..sort((a, b) => a.date.compareTo(b.date));

    for (final summary in sorted) {
      for (final metric in _trendMetrics) {
        final value = summary.metricsSnapshot[metric];
        if (value != null) {
          result[metric]!.add((summary.date, (value as num).toDouble()));
        }
      }
    }

    return result;
  }
}