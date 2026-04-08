import '../models/biometrics_record.dart';
import '../models/nudge_rule.dart';

/// Evaluates nudge rules against today's biometrics data.
///
/// Supported conditions:
///   sleep_hours < N, resting_hr > N, steps < N, hrv_ms < N
class NudgeEvaluator {
  /// Returns active nudges (rules whose conditions match today's data).
  static List<NudgeRule> evaluate(
    List<NudgeRule> rules,
    BiometricsRecord? biometrics,
  ) {
    if (biometrics == null || rules.isEmpty) return [];

    final active = <NudgeRule>[];
    for (final rule in rules) {
      if (_matches(rule.condition, biometrics)) {
        active.add(rule);
      }
    }
    // Sort by priority (lowest number = highest priority)
    active.sort((a, b) => a.priority.compareTo(b.priority));
    return active;
  }

  static bool _matches(String condition, BiometricsRecord bio) {
    // Parse simple conditions like "sleep_hours < 6" or "resting_hr > 70"
    final parts = condition.split(RegExp(r'\s+'));
    if (parts.length != 3) return false;

    final metric = parts[0];
    final op = parts[1];
    final threshold = double.tryParse(parts[2]);
    if (threshold == null) return false;

    final value = _getMetric(metric, bio);
    if (value == null) return false;

    switch (op) {
      case '<':
        return value < threshold;
      case '>':
        return value > threshold;
      case '<=':
        return value <= threshold;
      case '>=':
        return value >= threshold;
      default:
        return false;
    }
  }

  static double? _getMetric(String metric, BiometricsRecord bio) {
    switch (metric) {
      case 'sleep_hours':
        return bio.sleepSeconds != null ? bio.sleepSeconds! / 3600.0 : null;
      case 'resting_hr':
        return bio.restingHr?.toDouble();
      case 'steps':
        return bio.steps?.toDouble();
      case 'hrv_ms':
        return bio.hrvMs?.toDouble();
      case 'spo2_pct':
        return bio.spo2Pct;
      case 'sleep_score':
        return bio.sleepScore?.toDouble();
      default:
        return null;
    }
  }
}
