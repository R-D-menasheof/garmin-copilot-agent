import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:health/health.dart';

import 'package:vitalis/services/health_connect.dart';

class _FakeHealthClient implements HealthClient {
  _FakeHealthClient({
    this.sdkStatus = HealthConnectSdkStatus.sdkAvailable,
    this.hasGrantedPermissions = false,
    this.requestAuthorizationResult = true,
    this.points = const [],
  });

  final HealthConnectSdkStatus sdkStatus;
  final bool hasGrantedPermissions;
  final bool requestAuthorizationResult;
  final List<HealthDataPoint> points;

  bool configured = false;

  @override
  Future<void> configure({bool useHealthConnectIfAvailable = false}) async {
    configured = useHealthConnectIfAvailable;
  }

  @override
  Future<HealthConnectSdkStatus?> getHealthConnectSdkStatus() async => sdkStatus;

  @override
  Future<List<HealthDataPoint>> getHealthDataFromTypes({
    required List<HealthDataType> types,
    required DateTime startTime,
    required DateTime endTime,
    bool includeManualEntry = true,
  }) async => points;

  @override
  Future<bool?> hasPermissions(
    List<HealthDataType> types, {
    List<HealthDataAccess>? permissions,
  }) async => hasGrantedPermissions;

  @override
  Future<bool> requestAuthorization(
    List<HealthDataType> types, {
    List<HealthDataAccess>? permissions,
  }) async => requestAuthorizationResult;
}

HealthDataPoint _numericPoint({
  required HealthDataType type,
  required num value,
  required DateTime from,
  DateTime? to,
}) {
  return HealthDataPoint(
    value: NumericHealthValue(numericValue: value),
    type: type,
    unit: dataTypeToUnit[type] ?? HealthDataUnit.NO_UNIT,
    dateFrom: from,
    dateTo: to ?? from,
    sourcePlatform: HealthPlatformType.googleHealthConnect,
    sourceDeviceId: 'device',
    sourceId: 'source',
    sourceName: 'Garmin',
  );
}

void main() {
  test('readDay aggregates real Health Connect metrics', () async {
    final day = DateTime(2026, 4, 5);
    final service = HealthConnectService(
      healthClient: _FakeHealthClient(
        points: [
          _numericPoint(
            type: HealthDataType.RESTING_HEART_RATE,
            value: 58,
            from: day,
          ),
          _numericPoint(
            type: HealthDataType.HEART_RATE,
            value: 64,
            from: day.add(const Duration(hours: 1)),
          ),
          _numericPoint(
            type: HealthDataType.HEART_RATE,
            value: 92,
            from: day.add(const Duration(hours: 2)),
          ),
          _numericPoint(
            type: HealthDataType.STEPS,
            value: 5000,
            from: day,
          ),
          _numericPoint(
            type: HealthDataType.STEPS,
            value: 3500,
            from: day.add(const Duration(hours: 4)),
          ),
          _numericPoint(
            type: HealthDataType.ACTIVE_ENERGY_BURNED,
            value: 420,
            from: day,
          ),
          _numericPoint(
            type: HealthDataType.TOTAL_CALORIES_BURNED,
            value: 2640,
            from: day,
          ),
          _numericPoint(
            type: HealthDataType.BLOOD_OXYGEN,
            value: 97,
            from: day,
          ),
          _numericPoint(
            type: HealthDataType.WEIGHT,
            value: 111.4,
            from: day,
          ),
          _numericPoint(
            type: HealthDataType.SLEEP_SESSION,
            value: 0,
            from: day,
            to: day.add(const Duration(hours: 7, minutes: 15)),
          ),
        ],
      ),
      platformOverride: TargetPlatform.android,
      isWebOverride: false,
    );

    final granted = await service.requestPermissions();
    final record = await service.readDay(day);

    expect(granted, isTrue);
    expect(record.restingHr, 58);
    expect(record.avgHr, 78);
    expect(record.maxHr, 92);
    expect(record.steps, 8500);
    expect(record.activeCalories, 420);
    expect(record.totalCalories, 2640);
    expect(record.spo2Pct, 97);
    expect(record.weightKg, 111.4);
    expect(record.sleepSeconds, 26100);
  });
}