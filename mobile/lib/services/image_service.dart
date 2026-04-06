import 'dart:io';
import 'dart:typed_data';
import 'package:image_picker/image_picker.dart';

/// Camera and gallery image capture service.
class ImageService {
  final ImagePicker _picker;

  ImageService({ImagePicker? picker}) : _picker = picker ?? ImagePicker();

  Future<Uint8List?> captureFromCamera() async {
    final file = await _picker.pickImage(
      source: ImageSource.camera,
      maxWidth: 1024,
      imageQuality: 85,
    );
    if (file == null) return null;
    final bytes = await file.readAsBytes();
    // Clean up temporary picker file after reading bytes
    try {
      await File(file.path).delete();
    } catch (_) {}
    return bytes;
  }

  Future<Uint8List?> pickFromGallery() async {
    final file = await _picker.pickImage(
      source: ImageSource.gallery,
      maxWidth: 1024,
      imageQuality: 85,
    );
    return file?.readAsBytes();
  }
}
