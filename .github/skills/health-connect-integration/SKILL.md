---
name: health-connect-integration
description: "Android Health Connect integration for Vitalis mobile app. Flutter health package, data types (vitals, activity, sleep, body, nutrition), permission flow, Garmin-to-Health-Connect mapping, background sync strategy. Use when: Health Connect, wearable data, biometrics sync, Garmin data in mobile, heart rate, HRV, SpO2, sleep stages, steps."
---

# Skill: Health Connect Integration

## Overview

The Vitalis mobile app reads wearable health data via Android's Health Connect API. Garmin Connect syncs data to Health Connect, and our Flutter app reads it using the `health` package.

## Data Flow

```
Garmin Venu 4 → Garmin Connect App → Health Connect → Vitalis Flutter App
                                                          ↓
                                                   BiometricsRecord
                                                          ↓
                                                   POST /api/v1/biometrics
                                                          ↓
                                                   Azure Blob Storage
```

## Data Types to Read

### Vitals
| Health Connect Type | Maps To | Unit |
|---|---|---|
| `HEART_RATE` | `BiometricsRecord.resting_hr` | bpm (use min of day as resting) |
| `HEART_RATE_VARIABILITY_RMSSD` | `BiometricsRecord.hrv_ms` | ms |
| `OXYGEN_SATURATION` | `BiometricsRecord.spo2_pct` | % |
| `BODY_TEMPERATURE` | (future) | °C |
| `BLOOD_PRESSURE` | (future, if available) | mmHg |

### Activity
| Health Connect Type | Maps To | Unit |
|---|---|---|
| `STEPS` | `BiometricsRecord.steps` | count |
| `ACTIVE_CALORIES_BURNED` | `BiometricsRecord.active_calories` | kcal |
| `EXERCISE_SESSION` | (activity log) | type + duration |
| `DISTANCE` | (activity log) | meters |

### Sleep
| Health Connect Type | Maps To | Unit |
|---|---|---|
| `SLEEP_SESSION` | `BiometricsRecord.sleep_seconds` | seconds (total) |
| Sleep stages (AWAKE, LIGHT, DEEP, REM) | (detailed breakdown) | seconds each |

### Body Composition
| Health Connect Type | Maps To | Unit |
|---|---|---|
| `WEIGHT` | `BiometricsRecord.weight_kg` | kg |
| `BODY_FAT` | `BiometricsRecord.body_fat_pct` | % |
| `BASAL_METABOLIC_RATE` | (used for calorie targets) | kcal/day |

## Flutter Implementation

### Package

```yaml
dependencies:
  health: ^10.0.0
```

### Permission Request

```dart
class HealthConnectService {
  final Health _health = Health();

  static const _types = [
    HealthDataType.HEART_RATE,
    HealthDataType.HEART_RATE_VARIABILITY_RMSSD,
    HealthDataType.BLOOD_OXYGEN,
    HealthDataType.STEPS,
    HealthDataType.ACTIVE_CALORIES_BURNED,
    HealthDataType.SLEEP_SESSION,
    HealthDataType.WEIGHT,
    HealthDataType.BODY_FAT_PERCENTAGE,
  ];

  static const _permissions = [
    HealthDataAccess.READ,
    HealthDataAccess.READ,
    HealthDataAccess.READ,
    HealthDataAccess.READ,
    HealthDataAccess.READ,
    HealthDataAccess.READ,
    HealthDataAccess.READ,
    HealthDataAccess.READ,
  ];

  Future<bool> requestPermissions() async {
    final hasPermissions = await _health.hasPermissions(
      _types, permissions: _permissions,
    );
    if (hasPermissions != true) {
      return await _health.requestAuthorization(
        _types, permissions: _permissions,
      );
    }
    return true;
  }
```

### Read Data for a Day

```dart
  Future<BiometricsRecord> readDay(DateTime date) async {
    final start = DateTime(date.year, date.month, date.day);
    final end = start.add(const Duration(days: 1));

    final data = await _health.getHealthDataFromTypes(
      types: _types,
      startTime: start,
      endTime: end,
    );

    int? restingHr;
    int? hrv;
    double? spo2;
    int? steps;
    int? activeCal;
    int? sleepSec;
    double? weight;
    double? bodyFat;

    for (final point in data) {
      switch (point.type) {
        case HealthDataType.HEART_RATE:
          final val = (point.value as NumericHealthValue).numericValue.toInt();
          restingHr = (restingHr == null) ? val : min(restingHr, val);
        case HealthDataType.HEART_RATE_VARIABILITY_RMSSD:
          hrv = (point.value as NumericHealthValue).numericValue.toInt();
        case HealthDataType.BLOOD_OXYGEN:
          spo2 = (point.value as NumericHealthValue).numericValue.toDouble();
        case HealthDataType.STEPS:
          steps = (steps ?? 0) +
              (point.value as NumericHealthValue).numericValue.toInt();
        case HealthDataType.ACTIVE_CALORIES_BURNED:
          activeCal = (activeCal ?? 0) +
              (point.value as NumericHealthValue).numericValue.toInt();
        case HealthDataType.SLEEP_SESSION:
          sleepSec = (sleepSec ?? 0) +
              point.dateTo.difference(point.dateFrom).inSeconds;
        case HealthDataType.WEIGHT:
          weight = (point.value as NumericHealthValue).numericValue.toDouble();
        case HealthDataType.BODY_FAT_PERCENTAGE:
          bodyFat = (point.value as NumericHealthValue).numericValue.toDouble();
        default:
          break;
      }
    }

    return BiometricsRecord(
      date: date,
      restingHr: restingHr,
      hrvMs: hrv,
      spo2Pct: spo2,
      steps: steps,
      activeCalories: activeCal,
      sleepSeconds: sleepSec,
      weightKg: weight,
      bodyFatPct: bodyFat,
    );
  }
}
```

## Sync Strategy

### When to Sync
1. **On app open** — read today's data from Health Connect
2. **Background** — every 4 hours via `workmanager` package (Android WorkManager)
3. **Manual pull-to-refresh** — user triggers from settings

### Diff-Based Sync
- Track last-synced timestamp in Isar
- Only request data from Health Connect since last sync
- Post only new/updated records to API
- Avoid duplicating data in Blob Storage

```dart
Future<void> syncToCloud(ApiClient api) async {
  final lastSync = await _getLastSyncTime();
  final now = DateTime.now();

  for (var d = lastSync; d.isBefore(now); d = d.add(const Duration(days: 1))) {
    final record = await readDay(d);
    await api.postBiometrics(record);
  }

  await _setLastSyncTime(now);
}
```

## Garmin ↔ Health Connect Overlap

Garmin Connect writes to Health Connect. The existing `scripts/sync.py` provides MORE data than Health Connect (Body Battery, Training Readiness, stress, etc.). Health Connect is used for:
- Real-time mobile access without running a full sync
- Data types that the Garmin API doesn't expose well to third-party apps

| Data | From Health Connect | Additional from Garmin API |
|------|-------------------|---------------------------|
| Heart rate | ✓ | HR zones, activity HR |
| HRV | ✓ | Nightly HRV averages |
| SpO2 | ✓ | — |
| Steps | ✓ | Hourly breakdown |
| Sleep | ✓ (stages) | Sleep score, respiration |
| Weight | ✓ | — |
| Body Battery | ✗ | ✓ (Garmin proprietary) |
| Training Readiness | ✗ | ✓ (Garmin proprietary) |
| Stress | ✗ | ✓ (all-day stress) |
| VO2max | ✗ | ✓ |

## Android Configuration

### AndroidManifest.xml

```xml
<uses-permission android:name="android.permission.health.READ_HEART_RATE"/>
<uses-permission android:name="android.permission.health.READ_HEART_RATE_VARIABILITY"/>
<uses-permission android:name="android.permission.health.READ_OXYGEN_SATURATION"/>
<uses-permission android:name="android.permission.health.READ_STEPS"/>
<uses-permission android:name="android.permission.health.READ_ACTIVE_CALORIES_BURNED"/>
<uses-permission android:name="android.permission.health.READ_SLEEP"/>
<uses-permission android:name="android.permission.health.READ_WEIGHT"/>
<uses-permission android:name="android.permission.health.READ_BODY_FAT"/>
```

## Testing

Mock the `health` package in Flutter tests:

```dart
test('readDay aggregates steps from multiple data points', () async {
  final service = HealthConnectService(mockHealth);
  when(mockHealth.getHealthDataFromTypes(...)).thenAnswer((_) async => [
    HealthDataPoint(type: HealthDataType.STEPS, value: NumericHealthValue(5000)),
    HealthDataPoint(type: HealthDataType.STEPS, value: NumericHealthValue(3500)),
  ]);

  final record = await service.readDay(DateTime(2026, 4, 4));
  expect(record.steps, equals(8500));
});
```
