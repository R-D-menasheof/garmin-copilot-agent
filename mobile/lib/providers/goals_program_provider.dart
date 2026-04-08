import 'package:flutter/foundation.dart';

import '../models/goal_program.dart';
import '../services/api_client.dart';

class GoalsProgramProvider extends ChangeNotifier {
  final ApiClient _api;

  List<GoalProgram> _programs = [];
  List<GoalProgram> get programs => List.unmodifiable(_programs);

  bool _loading = false;
  bool get loading => _loading;

  GoalsProgramProvider(this._api);

  Future<void> loadPrograms() async {
    _loading = true;
    notifyListeners();
    try {
      _programs = await _api.getGoalPrograms();
    } catch (_) {
      // No programs yet
    } finally {
      _loading = false;
      notifyListeners();
    }
  }
}
