import 'package:flutter/foundation.dart';

import '../models/recommendation_status.dart';
import '../services/api_client.dart';

class RecommendationProvider extends ChangeNotifier {
  final ApiClient _api;

  List<RecommendationStatus> _statuses = [];
  List<RecommendationStatus> get statuses => List.unmodifiable(_statuses);

  bool _loading = false;
  bool get loading => _loading;

  RecommendationProvider(this._api);

  Future<void> loadStatuses() async {
    _loading = true;
    notifyListeners();
    try {
      _statuses = await _api.getRecommendationStatuses();
    } catch (_) {
      // Silently ignore — statuses are empty until first interaction
    } finally {
      _loading = false;
      notifyListeners();
    }
  }

  RecStatus getStatus(String recId) {
    final match = _statuses.where((s) => s.recId == recId);
    return match.isEmpty ? RecStatus.pending : match.first.status;
  }

  Future<void> markDone(String recId) async {
    _updateLocal(recId, RecStatus.done);
    await _api.postRecommendationStatus(recId, RecStatus.done);
  }

  Future<void> markSnoozed(String recId) async {
    _updateLocal(recId, RecStatus.snoozed);
    await _api.postRecommendationStatus(recId, RecStatus.snoozed);
  }

  Future<void> markPending(String recId) async {
    _updateLocal(recId, RecStatus.pending);
    await _api.postRecommendationStatus(recId, RecStatus.pending);
  }

  void _updateLocal(String recId, RecStatus status) {
    final idx = _statuses.indexWhere((s) => s.recId == recId);
    if (idx >= 0) {
      _statuses[idx] = _statuses[idx].copyWith(
        status: status,
        updatedAt: DateTime.now(),
      );
    } else {
      _statuses.add(RecommendationStatus(
        recId: recId,
        status: status,
        updatedAt: DateTime.now(),
      ));
    }
    notifyListeners();
  }
}
