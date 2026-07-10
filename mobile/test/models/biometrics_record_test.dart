import 'package:flutter_test/flutter_test.dart';
import 'package:vitalis/models/biometrics_record.dart';

void main() {
  group('BiometricsRecord', () {
    test('fromJson parses snake_case fields including vo2max', () {
      final record = BiometricsRecord.fromJson({
        'date': '2026-04-04',
        'resting_hr': 64,
        'hrv_ms': 28,
        'weight_kg': 112.0,
        'body_fat_pct': 30.5,
        'sleep_seconds': 21600,
        'vo2max': 42.5,
      });

      expect(record.date, DateTime(2026, 4, 4));
      expect(record.restingHr, 64);
      expect(record.hrvMs, 28);
      expect(record.weightKg, 112.0);
      expect(record.bodyFatPct, 30.5);
      expect(record.sleepSeconds, 21600);
      expect(record.vo2max, 42.5);
    });

    test('vo2max round-trips through toJson/fromJson', () {
      final original = BiometricsRecord(
        date: DateTime(2026, 4, 4),
        vo2max: 39.8,
      );

      final restored = BiometricsRecord.fromJson(original.toJson());
      expect(restored.vo2max, 39.8);
    });

    test('missing vo2max is null', () {
      final record = BiometricsRecord.fromJson({'date': '2026-04-04'});
      expect(record.vo2max, isNull);
    });
  });
}
