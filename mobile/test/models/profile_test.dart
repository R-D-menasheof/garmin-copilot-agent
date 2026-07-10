import 'package:flutter_test/flutter_test.dart';
import 'package:vitalis/models/profile.dart';

void main() {
  group('Profile', () {
    final json = <String, dynamic>{
      'display_name': 'רועי',
      'email': 'r@x.com',
      'date_of_birth': '1989-06-25',
      'sex': 'Male',
      'height_cm': 183.0,
      'goals': ['ירידה במשקל'],
      'dietary_preferences': ['צום לסירוגין'],
      'notes': 'note',
      'current_medications': [
        {'name': 'Steronase', 'type': 'spray', 'stopped': null},
        {'name': 'Telfast', 'stopped': '2026-03-13'},
      ],
      'supplements': [
        {'name': 'Magnesium', 'dosage': '200mg'},
      ],
      'weight_kg': 106.3,
      'bmi': 31.7,
      'vo2max': 38.4,
      'resting_heart_rate': 60,
      'devices': [
        {'name': 'Venu', 'type': 'watch'},
      ],
      'onboarded': true,
    };

    test('fromJson parses editable and read-only fields', () {
      final p = Profile.fromJson(json);
      expect(p.displayName, 'רועי');
      expect(p.sex, 'Male');
      expect(p.heightCm, 183.0);
      expect(p.goals, ['ירידה במשקל']);
      expect(p.dietaryPreferences, ['צום לסירוגין']);
      expect(p.currentMedications, hasLength(2));
      expect(p.currentMedications[0].isStopped, false);
      expect(p.currentMedications[1].isStopped, true);
      expect(p.supplements.first.dosage, '200mg');
      expect(p.weightKg, 106.3);
      expect(p.restingHeartRate, 60);
      expect(p.devices.first.name, 'Venu');
      expect(p.onboarded, true);
    });

    test('ageYears computes from date_of_birth', () {
      final p = Profile.fromJson({'date_of_birth': '1989-06-25'});
      expect(p.ageYears, greaterThan(35));
      expect(p.ageYears, lessThan(40));
    });

    test('ageYears falls back to legacy age', () {
      final p = Profile.fromJson({'age': 30.0});
      expect(p.ageYears, 30.0);
    });

    test('defaults apply for an empty json', () {
      final p = Profile.fromJson({});
      expect(p.displayName, '');
      expect(p.goals, isEmpty);
      expect(p.currentMedications, isEmpty);
      expect(p.onboarded, false);
    });

    test('toJson round-trips medications, supplements and goals', () {
      final back = Profile.fromJson(Profile.fromJson(json).toJson());
      expect(back.currentMedications[1].stopped, '2026-03-13');
      expect(back.supplements.first.name, 'Magnesium');
      expect(back.goals, ['ירידה במשקל']);
    });

    test('Medication.copyWith sets the stopped date', () {
      const m = Medication(name: 'X');
      final stopped = m.copyWith(stopped: '2026-07-06');
      expect(stopped.isStopped, true);
      expect(stopped.name, 'X');
    });
  });
}
