import 'package:flutter_test/flutter_test.dart';

import 'package:vitalis/services/training_day_service.dart';
import 'package:vitalis/models/training_program.dart';

TrainingProgram _programWith(List<TrainingSession> sessions) => TrainingProgram(
      id: 'p1',
      name: 'מבצע VO2max 40',
      goal: 'vo2max',
      durationWeeks: 8,
      weeks: [TrainingWeek(weekNumber: 1, sessions: sessions)],
      createdAt: DateTime(2026, 1, 1),
    );

void main() {
  group('TrainingDayService', () {
    test('returns null when no active program provided', () {
      final result = TrainingDayService.isTrainingDay(DateTime(2026, 7, 5), null);
      expect(result, isNull);
    });

    test('matches Hebrew weekday name correctly (Sunday -> ראשון)', () {
      // 2026-07-05 is a Sunday.
      final sunday = DateTime(2026, 7, 5);
      expect(sunday.weekday, DateTime.sunday);

      final program = _programWith([
        const TrainingSession(day: 'ראשון', type: 'swimming'),
      ]);

      final result = TrainingDayService.isTrainingDay(sunday, program);
      expect(result, true);
    });

    test('returns true when active program has non-rest session matching weekday', () {
      // 2026-07-08 is a Wednesday.
      final wednesday = DateTime(2026, 7, 8);
      expect(wednesday.weekday, DateTime.wednesday);

      final program = _programWith([
        const TrainingSession(day: 'רביעי', type: 'strength'),
      ]);

      final result = TrainingDayService.isTrainingDay(wednesday, program);
      expect(result, true);
    });

    test('returns false when active program has type=rest session for that weekday', () {
      final wednesday = DateTime(2026, 7, 8);

      final program = _programWith([
        const TrainingSession(day: 'רביעי', type: 'rest'),
      ]);

      final result = TrainingDayService.isTrainingDay(wednesday, program);
      expect(result, false);
    });

    test('returns false when no session is scheduled for that weekday', () {
      final wednesday = DateTime(2026, 7, 8);

      final program = _programWith([
        const TrainingSession(day: 'ראשון', type: 'swimming'),
      ]);

      final result = TrainingDayService.isTrainingDay(wednesday, program);
      expect(result, false);
    });

    test('matches English weekday names (real agent data uses "Sunday", "Monday", ...)', () {
      // 2026-07-05 is a Sunday; 2026-07-08 is a Wednesday.
      final sunday = DateTime(2026, 7, 5);
      final wednesday = DateTime(2026, 7, 8);

      final program = _programWith([
        const TrainingSession(day: 'Sunday', type: 'pilates'),
        const TrainingSession(day: 'Wednesday', type: 'rest'),
      ]);

      expect(TrainingDayService.isTrainingDay(sunday, program), true);
      expect(TrainingDayService.isTrainingDay(wednesday, program), false);
    });
  });
}
