import 'package:flutter/foundation.dart';

import '../models/training_program.dart';
import '../services/api_client.dart';

class TrainingProvider extends ChangeNotifier {
  final ApiClient _api;

  TrainingProgram? _activeProgram;
  TrainingProgram? get activeProgram => _activeProgram;

  bool _loading = false;
  bool get loading => _loading;

  TrainingProvider(this._api);

  Future<void> loadActiveProgram() async {
    _loading = true;
    notifyListeners();
    try {
      _activeProgram = await _api.getActiveTrainingProgram();
    } catch (_) {
      // No program available
    } finally {
      _loading = false;
      notifyListeners();
    }
  }

  Future<void> toggleSession(int weekIdx, int sessionIdx, bool completed) async {
    if (_activeProgram == null) return;

    // Update local state optimistically
    final weeks = _activeProgram!.weeks.toList();
    final sessions = weeks[weekIdx].sessions.toList();
    sessions[sessionIdx] = sessions[sessionIdx].copyWith(completed: completed);
    weeks[weekIdx] = TrainingWeek(
      weekNumber: weeks[weekIdx].weekNumber,
      sessions: sessions,
      notes: weeks[weekIdx].notes,
    );
    _activeProgram = TrainingProgram(
      id: _activeProgram!.id,
      name: _activeProgram!.name,
      goal: _activeProgram!.goal,
      durationWeeks: _activeProgram!.durationWeeks,
      weeks: weeks,
      createdAt: _activeProgram!.createdAt,
      active: _activeProgram!.active,
    );
    notifyListeners();

    try {
      await _api.patchTrainingSession(weekIdx, sessionIdx, completed);
    } catch (_) {
      // Offline — will sync later
    }
  }
}
