import 'package:flutter/foundation.dart';

import '../models/sleep_models.dart';
import '../services/api_client.dart';

class SleepProvider extends ChangeNotifier {
  final ApiClient _api;

  SleepChecklist? _checklist;
  SleepChecklist? get checklist => _checklist;

  SleepEntry? _todayEntry;
  SleepEntry? get todayEntry => _todayEntry;

  bool _loading = false;
  bool get loading => _loading;

  SleepProvider(this._api);

  Future<void> loadProtocol() async {
    _loading = true;
    notifyListeners();
    try {
      _checklist = await _api.getSleepProtocol();
    } catch (_) {
      // Use default checklist
      _checklist ??= _defaultChecklist();
    } finally {
      _loading = false;
      notifyListeners();
    }
  }

  void toggleChecklistItem(String itemId, bool checked) {
    if (_checklist == null) return;
    for (final item in _checklist!.items) {
      if (item.id == itemId) {
        item.checked = checked;
        break;
      }
    }
    notifyListeners();
  }

  Future<void> rateSleep(int rating) async {
    final now = DateTime.now();
    _todayEntry = SleepEntry(
      date: now,
      rating: rating,
      checklistCompleted: _checklist?.items.where((i) => i.checked).length ?? 0,
    );
    notifyListeners();
    try {
      await _api.postSleepEntry(_todayEntry!);
    } catch (_) {
      // Offline — entry will sync later
    }
  }

  static SleepChecklist _defaultChecklist() => SleepChecklist(items: [
        ChecklistItem(id: 'caffeine', labelHe: 'ללא קפאין אחרי 14:00', category: 'habits'),
        ChecklistItem(id: 'screens', labelHe: 'ללא מסכים אחרי 22:00', category: 'wind_down'),
        ChecklistItem(id: 'magnesium', labelHe: 'מגנזיום נלקח', category: 'habits'),
        ChecklistItem(id: 'cool_room', labelHe: 'חדר קריר (18-20°C)', category: 'environment'),
        ChecklistItem(id: 'bed_target', labelHe: 'במיטה עד 23:00', category: 'wind_down'),
      ]);
}
