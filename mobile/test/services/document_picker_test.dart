import 'package:flutter_test/flutter_test.dart';

import 'package:vitalis/services/document_picker.dart';

void main() {
  group('contentTypeForFilename', () {
    test('maps known extensions to MIME types (case-insensitive)', () {
      expect(contentTypeForFilename('scan.PNG'), 'image/png');
      expect(contentTypeForFilename('report.pdf'), 'application/pdf');
      expect(contentTypeForFilename('photo.jpg'), 'image/jpeg');
      expect(contentTypeForFilename('photo.jpeg'), 'image/jpeg');
    });

    test('defaults to jpeg for camera captures without an extension', () {
      expect(contentTypeForFilename('IMG_1234'), 'image/jpeg');
    });
  });
}
