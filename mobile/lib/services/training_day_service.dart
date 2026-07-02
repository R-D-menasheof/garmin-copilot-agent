import '../models/training_program.dart';

/// Determines whether a given date is a training day, based on the
/// scheduled sessions in an active [TrainingProgram].
class TrainingDayService {
  /// Accepted session `day` labels per `DateTime.weekday`, normalized to
  /// lowercase. Agent-generated programs use English names ("Sunday",
  /// "Monday", …); user/manual data may use Hebrew names (ראשון, שני, …).
  /// Both are matched.
  static const Map<int, List<String>> _dayNamesByWeekday = {
    DateTime.monday: ['monday', 'שני'],
    DateTime.tuesday: ['tuesday', 'שלישי'],
    DateTime.wednesday: ['wednesday', 'רביעי'],
    DateTime.thursday: ['thursday', 'חמישי'],
    DateTime.friday: ['friday', 'שישי'],
    DateTime.saturday: ['saturday', 'שבת'],
    DateTime.sunday: ['sunday', 'ראשון'],
  };

  /// Returns `true` if [date] has a scheduled non-rest session in
  /// [activeProgram], `false` if it has a rest session (or no session at
  /// all) scheduled for that weekday, or `null` if no active program is
  /// provided — callers should fall back to a default heuristic in that case.
  static bool? isTrainingDay(DateTime date, TrainingProgram? activeProgram) {
    if (activeProgram == null) {
      return null;
    }

    final names = _dayNamesByWeekday[date.weekday] ?? const <String>[];
    for (final week in activeProgram.weeks) {
      for (final session in week.sessions) {
        if (names.contains(session.day.toLowerCase().trim())) {
          return session.type != 'rest';
        }
      }
    }
    return false;
  }
}
