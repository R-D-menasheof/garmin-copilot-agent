/// Daily biometrics from Health Connect / wearable.
/// Mirrors Python BiometricsRecord model.
/// Captures ALL available data from Garmin via Health Connect.
class BiometricsRecord {
  final DateTime date;

  // ── Heart ──────────────────────────────────────────────
  final int? restingHr;         // bpm (lowest of the day)
  final int? avgHr;             // bpm (average of the day)
  final int? maxHr;             // bpm (peak during activity)
  final int? hrvMs;             // ms (RMSSD, nightly)

  // ── Vitals ─────────────────────────────────────────────
  final double? spo2Pct;        // % (blood oxygen)
  final double? bodyTempC;      // °C (body/wrist temperature)
  final double? respiratoryRate; // breaths/min
  final int? bpSystolic;        // mmHg (if available)
  final int? bpDiastolic;       // mmHg (if available)

  // ── Activity ───────────────────────────────────────────
  final int? steps;             // total steps
  final int? activeCalories;    // kcal (active energy burned)
  final int? totalCalories;     // kcal (total incl. BMR)
  final int? floorsClimbed;     // flights
  final double? distanceMeters; // total distance (walk+run+cycle)
  final int? exerciseMinutes;   // active/exercise minutes
  final int? intensityMinutes;  // vigorous + moderate

  // ── Sleep ──────────────────────────────────────────────
  final int? sleepSeconds;      // total sleep duration
  final int? deepSleepSeconds;  // deep stage
  final int? lightSleepSeconds; // light stage
  final int? remSleepSeconds;   // REM stage
  final int? awakeSleepSeconds; // awake during sleep session
  final int? sleepScore;        // Garmin sleep score (0-100)

  // ── Body ───────────────────────────────────────────────
  final double? weightKg;
  final double? bodyFatPct;
  final double? bmi;
  final double? basalMetabolicRate; // kcal/day (BMR)

  // ── Hydration ──────────────────────────────────────────
  final double? waterMl;        // water consumed (ml)

  const BiometricsRecord({
    required this.date,
    this.restingHr,
    this.avgHr,
    this.maxHr,
    this.hrvMs,
    this.spo2Pct,
    this.bodyTempC,
    this.respiratoryRate,
    this.bpSystolic,
    this.bpDiastolic,
    this.steps,
    this.activeCalories,
    this.totalCalories,
    this.floorsClimbed,
    this.distanceMeters,
    this.exerciseMinutes,
    this.intensityMinutes,
    this.sleepSeconds,
    this.deepSleepSeconds,
    this.lightSleepSeconds,
    this.remSleepSeconds,
    this.awakeSleepSeconds,
    this.sleepScore,
    this.weightKg,
    this.bodyFatPct,
    this.bmi,
    this.basalMetabolicRate,
    this.waterMl,
  });

  factory BiometricsRecord.fromJson(Map<String, dynamic> json) =>
      BiometricsRecord(
        date: DateTime.parse(json['date'] as String),
        // Heart
        restingHr: json['resting_hr'] as int?,
        avgHr: json['avg_hr'] as int?,
        maxHr: json['max_hr'] as int?,
        hrvMs: json['hrv_ms'] as int?,
        // Vitals
        spo2Pct: (json['spo2_pct'] as num?)?.toDouble(),
        bodyTempC: (json['body_temp_c'] as num?)?.toDouble(),
        respiratoryRate: (json['respiratory_rate'] as num?)?.toDouble(),
        bpSystolic: json['bp_systolic'] as int?,
        bpDiastolic: json['bp_diastolic'] as int?,
        // Activity
        steps: json['steps'] as int?,
        activeCalories: json['active_calories'] as int?,
        totalCalories: json['total_calories'] as int?,
        floorsClimbed: json['floors_climbed'] as int?,
        distanceMeters: (json['distance_meters'] as num?)?.toDouble(),
        exerciseMinutes: json['exercise_minutes'] as int?,
        intensityMinutes: json['intensity_minutes'] as int?,
        // Sleep
        sleepSeconds: json['sleep_seconds'] as int?,
        deepSleepSeconds: json['deep_sleep_seconds'] as int?,
        lightSleepSeconds: json['light_sleep_seconds'] as int?,
        remSleepSeconds: json['rem_sleep_seconds'] as int?,
        awakeSleepSeconds: json['awake_sleep_seconds'] as int?,
        sleepScore: json['sleep_score'] as int?,
        // Body
        weightKg: (json['weight_kg'] as num?)?.toDouble(),
        bodyFatPct: (json['body_fat_pct'] as num?)?.toDouble(),
        bmi: (json['bmi'] as num?)?.toDouble(),
        basalMetabolicRate: (json['basal_metabolic_rate'] as num?)?.toDouble(),
        // Hydration
        waterMl: (json['water_ml'] as num?)?.toDouble(),
      );

  Map<String, dynamic> toJson() => {
        'date': date.toIso8601String().split('T').first,
        // Heart
        if (restingHr != null) 'resting_hr': restingHr,
        if (avgHr != null) 'avg_hr': avgHr,
        if (maxHr != null) 'max_hr': maxHr,
        if (hrvMs != null) 'hrv_ms': hrvMs,
        // Vitals
        if (spo2Pct != null) 'spo2_pct': spo2Pct,
        if (bodyTempC != null) 'body_temp_c': bodyTempC,
        if (respiratoryRate != null) 'respiratory_rate': respiratoryRate,
        if (bpSystolic != null) 'bp_systolic': bpSystolic,
        if (bpDiastolic != null) 'bp_diastolic': bpDiastolic,
        // Activity
        if (steps != null) 'steps': steps,
        if (activeCalories != null) 'active_calories': activeCalories,
        if (totalCalories != null) 'total_calories': totalCalories,
        if (floorsClimbed != null) 'floors_climbed': floorsClimbed,
        if (distanceMeters != null) 'distance_meters': distanceMeters,
        if (exerciseMinutes != null) 'exercise_minutes': exerciseMinutes,
        if (intensityMinutes != null) 'intensity_minutes': intensityMinutes,
        // Sleep
        if (sleepSeconds != null) 'sleep_seconds': sleepSeconds,
        if (deepSleepSeconds != null) 'deep_sleep_seconds': deepSleepSeconds,
        if (lightSleepSeconds != null) 'light_sleep_seconds': lightSleepSeconds,
        if (remSleepSeconds != null) 'rem_sleep_seconds': remSleepSeconds,
        if (awakeSleepSeconds != null) 'awake_sleep_seconds': awakeSleepSeconds,
        if (sleepScore != null) 'sleep_score': sleepScore,
        // Body
        if (weightKg != null) 'weight_kg': weightKg,
        if (bodyFatPct != null) 'body_fat_pct': bodyFatPct,
        if (bmi != null) 'bmi': bmi,
        if (basalMetabolicRate != null) 'basal_metabolic_rate': basalMetabolicRate,
        // Hydration
        if (waterMl != null) 'water_ml': waterMl,
      };
}
