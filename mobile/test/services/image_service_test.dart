import 'dart:io';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:image_picker/image_picker.dart';

import 'package:vitalis/services/image_service.dart';

class _FakeImagePicker extends ImagePicker {
  _FakeImagePicker(this.path);

  final String path;

  @override
  Future<XFile?> pickImage({
    ImageSource source = ImageSource.gallery,
    double? maxWidth,
    double? maxHeight,
    int? imageQuality,
    CameraDevice preferredCameraDevice = CameraDevice.rear,
    bool requestFullMetadata = true,
  }) async {
    return XFile(path);
  }
}

void main() {
  test('captureFromCamera deletes the temporary picker file after reading bytes', () async {
    final tempDir = await Directory.systemTemp.createTemp('vitalis-image-test');
    final tempFile = File('${tempDir.path}\\meal.jpg');
    await tempFile.writeAsBytes(Uint8List.fromList(<int>[1, 2, 3]));

    final service = ImageService(picker: _FakeImagePicker(tempFile.path));

    final bytes = await service.captureFromCamera();

    expect(bytes, isNotNull);
    expect(await tempFile.exists(), isFalse);
  });
}