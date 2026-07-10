import 'package:flutter/foundation.dart';

import '../models/medical_upload.dart';
import '../services/api_client.dart';
import '../services/document_picker.dart';

/// State for the medical documents screen — list + upload (Phase 4b).
class MedicalProvider extends ChangeNotifier {
  final ApiClient _api;

  MedicalProvider(this._api);

  List<MedicalUpload> _documents = [];
  List<MedicalUpload> get documents => _documents;

  bool _loading = false;
  bool get loading => _loading;

  bool _uploading = false;
  bool get uploading => _uploading;

  String? _error;
  String? get error => _error;

  /// Load the user's uploaded documents from the API.
  Future<void> loadDocuments() async {
    _loading = true;
    _error = null;
    notifyListeners();
    try {
      _documents = await _api.getMedicalUploads();
    } catch (_) {
      _error = 'טעינת המסמכים נכשלה';
    } finally {
      _loading = false;
      notifyListeners();
    }
  }

  /// Upload a picked document; prepends it to the list on success.
  ///
  /// Returns true on success, false on failure (see [error]).
  Future<bool> uploadDocument(
    PickedDocument doc, {
    String category = '',
    String note = '',
  }) async {
    _uploading = true;
    _error = null;
    notifyListeners();
    try {
      final uploaded = await _api.uploadMedicalDocument(
        bytes: doc.bytes,
        filename: doc.filename,
        contentType: doc.contentType,
        category: category,
        note: note,
      );
      _documents = [uploaded, ..._documents];
      return true;
    } catch (_) {
      _error = 'העלאת המסמך נכשלה';
      return false;
    } finally {
      _uploading = false;
      notifyListeners();
    }
  }
}
