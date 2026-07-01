import 'package:flutter_test/flutter_test.dart';

import 'package:vitalis/models/day_tracking_override.dart';

void main() {
  group('DayTrackingOverride', () {
    test('fromJson round-trip', () {
      final override = DayTrackingOverride(
        date: DateTime(2026, 7, 1),
        tracked: false,
        note: 'נסעתי, לא תיעדתי כמו שצריך',
        updatedAt: DateTime(2026, 7, 1, 20, 0),
      );

      final json = override.toJson();
      expect(json['date'], '2026-07-01');
      expect(json['tracked'], false);
      expect(json['note'], 'נסעתי, לא תיעדתי כמו שצריך');

      final restored = DayTrackingOverride.fromJson(json);
      expect(restored.date, DateTime(2026, 7, 1));
      expect(restored.tracked, false);
      expect(restored.note, 'נסעתי, לא תיעדתי כמו שצריך');
    });

    test('fromJson defaults tracked to true when absent', () {
      final json = {
        'date': '2026-07-01',
        'updated_at': '2026-07-01T20:00:00.000',
      };
      final override = DayTrackingOverride.fromJson(json);
      expect(override.tracked, true);
      expect(override.note, '');
    });
  });
}
