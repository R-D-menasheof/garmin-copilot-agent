import 'dart:typed_data';

import 'package:file_picker/file_picker.dart';
import 'package:image_picker/image_picker.dart';

/// A picked document ready to upload: raw bytes + filename + MIME content type.
class PickedDocument {
  final Uint8List bytes;
  final String filename;
  final String contentType;

  const PickedDocument({
    required this.bytes,
    required this.filename,
    required this.contentType,
  });
}

/// Derive a MIME content type from a filename's extension.
///
/// Only the types the API accepts (pdf/jpeg/png) are recognised; anything
/// else (including camera captures with no extension) defaults to jpeg, which
/// is what the camera produces.
String contentTypeForFilename(String filename) {
  final lower = filename.toLowerCase();
  if (lower.endsWith('.png')) return 'image/png';
  if (lower.endsWith('.pdf')) return 'application/pdf';
  return 'image/jpeg';
}

/// Picks a medical document to upload — a camera photo, or a file (PDF/image).
///
/// Abstract so screens depend on the interface and tests can inject a fake.
abstract class DocumentPicker {
  /// Capture a document with the camera. Null if the user cancels.
  Future<PickedDocument?> pickFromCamera();

  /// Pick a PDF or image file from the device. Null if the user cancels.
  Future<PickedDocument?> pickFile();
}

/// [DocumentPicker] backed by [ImagePicker] (camera) + [FilePicker] (PDF/image).
class DeviceDocumentPicker implements DocumentPicker {
  final ImagePicker _imagePicker;

  DeviceDocumentPicker({ImagePicker? imagePicker})
      : _imagePicker = imagePicker ?? ImagePicker();

  @override
  Future<PickedDocument?> pickFromCamera() async {
    final file = await _imagePicker.pickImage(
      source: ImageSource.camera,
      maxWidth: 2048,
      imageQuality: 85,
    );
    if (file == null) return null;
    final bytes = await file.readAsBytes();
    return PickedDocument(
      bytes: bytes,
      filename: file.name,
      contentType: contentTypeForFilename(file.name),
    );
  }

  @override
  Future<PickedDocument?> pickFile() async {
    final result = await FilePicker.platform.pickFiles(
      type: FileType.custom,
      allowedExtensions: ['pdf', 'jpg', 'jpeg', 'png'],
      withData: true,
    );
    if (result == null || result.files.isEmpty) return null;
    final picked = result.files.first;
    final bytes = picked.bytes;
    if (bytes == null) return null;
    return PickedDocument(
      bytes: bytes,
      filename: picked.name,
      contentType: contentTypeForFilename(picked.name),
    );
  }
}
