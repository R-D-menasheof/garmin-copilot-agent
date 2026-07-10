/// A medication the user takes (or has stopped). Mirrors Python `Medication`.
class Medication {
  final String name;
  final String type;
  final String dose;
  final String frequency;
  final String purpose;
  final String? since;
  final String? stopped;
  final String note;

  const Medication({
    required this.name,
    this.type = '',
    this.dose = '',
    this.frequency = '',
    this.purpose = '',
    this.since,
    this.stopped,
    this.note = '',
  });

  bool get isStopped => stopped != null && stopped!.isNotEmpty;

  Medication copyWith({String? stopped}) => Medication(
        name: name,
        type: type,
        dose: dose,
        frequency: frequency,
        purpose: purpose,
        since: since,
        stopped: stopped ?? this.stopped,
        note: note,
      );

  factory Medication.fromJson(Map<String, dynamic> json) => Medication(
        name: json['name'] as String? ?? '',
        type: json['type'] as String? ?? '',
        dose: json['dose'] as String? ?? '',
        frequency: json['frequency'] as String? ?? '',
        purpose: json['purpose'] as String? ?? '',
        since: json['since'] as String?,
        stopped: json['stopped'] as String?,
        note: json['note'] as String? ?? '',
      );

  Map<String, dynamic> toJson() => {
        'name': name,
        'type': type,
        'dose': dose,
        'frequency': frequency,
        'purpose': purpose,
        'since': since,
        'stopped': stopped,
        'note': note,
      };
}

/// A supplement the user takes. Mirrors Python `Supplement`.
class Supplement {
  final String name;
  final String dosage;
  final String timing;
  final String? since;
  final String? stopped;
  final String note;

  const Supplement({
    required this.name,
    this.dosage = '',
    this.timing = '',
    this.since,
    this.stopped,
    this.note = '',
  });

  bool get isStopped => stopped != null && stopped!.isNotEmpty;

  Supplement copyWith({String? stopped}) => Supplement(
        name: name,
        dosage: dosage,
        timing: timing,
        since: since,
        stopped: stopped ?? this.stopped,
        note: note,
      );

  factory Supplement.fromJson(Map<String, dynamic> json) => Supplement(
        name: json['name'] as String? ?? '',
        dosage: json['dosage'] as String? ?? '',
        timing: json['timing'] as String? ?? '',
        since: json['since'] as String?,
        stopped: json['stopped'] as String?,
        note: json['note'] as String? ?? '',
      );

  Map<String, dynamic> toJson() => {
        'name': name,
        'dosage': dosage,
        'timing': timing,
        'since': since,
        'stopped': stopped,
        'note': note,
      };
}

/// A connected wearable device. Mirrors Python `Device`.
class Device {
  final String name;
  final String type;

  const Device({required this.name, this.type = ''});

  factory Device.fromJson(Map<String, dynamic> json) => Device(
        name: json['name'] as String? ?? '',
        type: json['type'] as String? ?? '',
      );

  Map<String, dynamic> toJson() => {'name': name, 'type': type};
}

/// User health profile — personal (editable) info plus auto-synced wearable
/// metrics (read-only). Mirrors Python `Profile`.
class Profile {
  // Identity
  final String displayName;
  final String email;

  // Personal — editable
  final String? dateOfBirth; // ISO date string (yyyy-MM-dd)
  final String? sex;
  final double? heightCm;
  final List<String> goals;
  final List<String> injuries;
  final List<String> dietaryPreferences;
  final String notes;
  final List<Medication> currentMedications;
  final List<Supplement> supplements;
  final double? age; // legacy fallback

  // Auto-synced from wearable — read-only in the UI
  final double? weightKg;
  final double? bodyFatPct;
  final double? bmi;
  final double? vo2max;
  final int? fitnessAge;
  final int? restingHeartRate;
  final List<Device> devices;
  final String? lastSynced;

  final bool onboarded;

  const Profile({
    this.displayName = '',
    this.email = '',
    this.dateOfBirth,
    this.sex,
    this.heightCm,
    this.goals = const [],
    this.injuries = const [],
    this.dietaryPreferences = const [],
    this.notes = '',
    this.currentMedications = const [],
    this.supplements = const [],
    this.age,
    this.weightKg,
    this.bodyFatPct,
    this.bmi,
    this.vo2max,
    this.fitnessAge,
    this.restingHeartRate,
    this.devices = const [],
    this.lastSynced,
    this.onboarded = false,
  });

  /// Age from [dateOfBirth], falling back to the legacy [age] field.
  double? get ageYears {
    if (dateOfBirth != null && dateOfBirth!.isNotEmpty) {
      final dob = DateTime.tryParse(dateOfBirth!);
      if (dob != null) {
        final days = DateTime.now().difference(dob).inDays;
        return (days / 365.25 * 10).round() / 10;
      }
    }
    return age;
  }

  static List<String> _stringList(dynamic raw) =>
      (raw as List?)?.map((e) => e.toString()).toList() ?? const [];

  factory Profile.fromJson(Map<String, dynamic> json) => Profile(
        displayName: json['display_name'] as String? ?? '',
        email: json['email'] as String? ?? '',
        dateOfBirth: json['date_of_birth'] as String?,
        sex: json['sex'] as String?,
        heightCm: (json['height_cm'] as num?)?.toDouble(),
        goals: _stringList(json['goals']),
        injuries: _stringList(json['injuries']),
        dietaryPreferences: _stringList(json['dietary_preferences']),
        notes: json['notes'] as String? ?? '',
        currentMedications: (json['current_medications'] as List?)
                ?.map((m) => Medication.fromJson(m as Map<String, dynamic>))
                .toList() ??
            const [],
        supplements: (json['supplements'] as List?)
                ?.map((s) => Supplement.fromJson(s as Map<String, dynamic>))
                .toList() ??
            const [],
        age: (json['age'] as num?)?.toDouble(),
        weightKg: (json['weight_kg'] as num?)?.toDouble(),
        bodyFatPct: (json['body_fat_pct'] as num?)?.toDouble(),
        bmi: (json['bmi'] as num?)?.toDouble(),
        vo2max: (json['vo2max'] as num?)?.toDouble(),
        fitnessAge: (json['fitness_age'] as num?)?.toInt(),
        restingHeartRate: (json['resting_heart_rate'] as num?)?.toInt(),
        devices: (json['devices'] as List?)
                ?.map((d) => Device.fromJson(d as Map<String, dynamic>))
                .toList() ??
            const [],
        lastSynced: json['last_synced'] as String?,
        onboarded: json['onboarded'] as bool? ?? false,
      );

  Map<String, dynamic> toJson() => {
        'display_name': displayName,
        'email': email,
        'date_of_birth': dateOfBirth,
        'sex': sex,
        'height_cm': heightCm,
        'goals': goals,
        'injuries': injuries,
        'dietary_preferences': dietaryPreferences,
        'notes': notes,
        'current_medications': currentMedications.map((m) => m.toJson()).toList(),
        'supplements': supplements.map((s) => s.toJson()).toList(),
        'age': age,
        'weight_kg': weightKg,
        'body_fat_pct': bodyFatPct,
        'bmi': bmi,
        'vo2max': vo2max,
        'fitness_age': fitnessAge,
        'resting_heart_rate': restingHeartRate,
        'devices': devices.map((d) => d.toJson()).toList(),
        'last_synced': lastSynced,
        'onboarded': onboarded,
      };
}
