import '../models/training_program.dart';

/// Determines whether a given date is a training day, based on the
/// scheduled sessions in an active [TrainingProgram].
class TrainingDayService {
  /// Hebrew weekday names indexed by `DateTime.weekday - 1`
  /// (`DateTime.weekday`: Monday = 1 ... Sunday = 7).
  static const List<String> _hebrewWeekdays = [
    'שני',
    'שלישי',
    'רביעי',
    'חמישי',
    'שישי',
    'שבת',
    'ראשון',
  ];

  /// Returns `true` if [date] has a scheduled non-rest session in
  /// [activeProgram], `false` if it has a rest session (or no session at
  /// all) scheduled for that weekday, or `null` if no active program is
  /// provided — callers should fall back to a default heuristic in that case.
  static bool? isTrainingDay(DateTime date, TrainingProgram? activeProgram) {
    if (activeProgram == null) {
      return null;
    }

    final dayName = _hebrewWeekdays[date.weekday - 1];
    for (final week in activeProgram.weeks) {
      for (final session in week.sessions) {
        if (session.day == dayName) {
          return session.type != 'rest';
        }
      }
    }
    return false;
  }
}
