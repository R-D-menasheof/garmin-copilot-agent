import 'package:flutter_test/flutter_test.dart';
import 'package:vitalis/models/medical_upload.dart';

void main() {
  group('MedicalUpload', () {
    test('fromJson parses all fields', () {
      final u = MedicalUpload.fromJson({
        'id': 'u1',
        'filename': 'labs.pdf',
        'content_type': 'application/pdf',
        'size_bytes': 1234,
        'category': 'blood',
        'note': 'fasting',
        'uploaded_at': '2026-07-05T10:30:00',
        'extracted': true,
      });
      expect(u.id, 'u1');
      expect(u.filename, 'labs.pdf');
      expect(u.contentType, 'application/pdf');
      expect(u.sizeBytes, 1234);
      expect(u.category, 'blood');
      expect(u.note, 'fasting');
      expect(u.uploadedAt, DateTime.parse('2026-07-05T10:30:00'));
      expect(u.extracted, true);
    });

    test('fromJson applies defaults for optional fields', () {
      final u = MedicalUpload.fromJson({
        'id': 'u2',
        'filename': 'scan.png',
        'uploaded_at': '2026-07-05T10:30:00',
      });
      expect(u.contentType, '');
      expect(u.sizeBytes, 0);
      expect(u.category, '');
      expect(u.note, '');
      expect(u.extracted, false);
    });

    test('toJson round-trips through fromJson', () {
      final u = MedicalUpload(
        id: 'u1',
        filename: 'labs.pdf',
        contentType: 'application/pdf',
        sizeBytes: 10,
        category: 'x',
        note: 'n',
        uploadedAt: DateTime.parse('2026-07-05T10:30:00'),
        extracted: true,
      );
      final back = MedicalUpload.fromJson(u.toJson());
      expect(back.id, 'u1');
      expect(back.filename, 'labs.pdf');
      expect(back.sizeBytes, 10);
      expect(back.extracted, true);
    });
  });
}
