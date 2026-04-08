import 'package:flutter_test/flutter_test.dart';

import 'package:vitalis/models/recommendation_status.dart';

void main() {
  group('RecommendationStatus', () {
    test('fromJson round-trip', () {
      final status = RecommendationStatus(
        recId: 'abc123',
        status: RecStatus.done,
        updatedAt: DateTime(2026, 4, 4, 12, 0),
      );

      final json = status.toJson();
      expect(json['rec_id'], 'abc123');
      expect(json['status'], 'done');

      final restored = RecommendationStatus.fromJson(json);
      expect(restored.recId, 'abc123');
      expect(restored.status, RecStatus.done);
    });

    test('fromJson defaults to pending', () {
      final json = {
        'rec_id': 'xyz',
        'status': 'pending',
        'updated_at': '2026-04-04T12:00:00.000',
      };
      final status = RecommendationStatus.fromJson(json);
      expect(status.status, RecStatus.pending);
    });

    test('id generation matches Python hash', () {
      // Python: hashlib.sha256('sleep:Extend sleep to 7h'.encode()).hexdigest()[:16]
      // = 'b546893149c51ec3'
      final id = RecommendationStatus.generateId('sleep', 'Extend sleep to 7h');
      expect(id, 'b546893149c51ec3');
    });
  });
}
