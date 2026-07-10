import 'package:flutter/foundation.dart';

import '../models/profile.dart';
import '../services/api_client.dart';

/// State for the profile view/edit screen (Phase 4).
///
/// Loads the user's profile and saves edits via `PATCH /v1/profile` (which
/// merges only the provided fields and never clobbers auto-synced wearable
/// data server-side).
class ProfileProvider extends ChangeNotifier {
  final ApiClient _api;

  ProfileProvider(this._api);

  Profile? _profile;
  Profile? get profile => _profile;

  bool _loading = false;
  bool get loading => _loading;

  bool _saving = false;
  bool get saving => _saving;

  String? _error;
  String? get error => _error;

  /// Load the profile from `GET /v1/profile`.
  Future<void> load() async {
    _loading = true;
    _error = null;
    notifyListeners();
    try {
      _profile = Profile.fromJson(await _api.getProfile());
    } catch (_) {
      _error = 'טעינת הפרופיל נכשלה';
    } finally {
      _loading = false;
      notifyListeners();
    }
  }

  /// Save the given field changes via `PATCH /v1/profile`.
  ///
  /// Returns true on success. Only the keys in [changes] are sent; the server
  /// merges them and preserves everything else (including wearable fields).
  Future<bool> save(Map<String, dynamic> changes) async {
    _saving = true;
    _error = null;
    notifyListeners();
    try {
      final updated = await _api.patchProfile(changes);
      _profile = Profile.fromJson(updated);
      return true;
    } catch (_) {
      _error = 'שמירת הפרופיל נכשלה';
      return false;
    } finally {
      _saving = false;
      notifyListeners();
    }
  }
}
