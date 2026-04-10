import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:health/health.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:vitalis/providers/biometrics_provider.dart';
import 'package:vitalis/services/api_client.dart';
import 'package:vitalis/services/health_connect.dart';

class _FakeHealthClient implements HealthClient {
  _FakeHealthClient({
    this.sdkStatus = HealthConnectSdkStatus.sdkAvailable,
    this.hasGrantedPermissions = false,
    this.requestAuthorizationResult = false,
    this.points = const <HealthDataPoint>[],
  });

  final HealthConnectSdkStatus sdkStatus;
  final bool hasGrantedPermissions;
  final bool requestAuthorizationResult;
  final List<HealthDataPoint> points;

  @override
  Future<void> configure({bool useHealthConnectIfAvailable = false}) async {}

  @override
  Future<HealthConnectSdkStatus?> getHealthConnectSdkStatus() async =>
      sdkStatus;

  @override
  Future<List<HealthDataPoint>> getHealthDataFromTypes({
    required List<HealthDataType> types,
    required DateTime startTime,
    required DateTime endTime,
    bool includeManualEntry = true,
  }) async =>
      points;

  @override
  Future<bool?> hasPermissions(
    List<HealthDataType> types, {
    List<HealthDataAccess>? permissions,
  }) async =>
      hasGrantedPermissions;

  @override
  Future<bool> requestAuthorization(
    List<HealthDataType> types, {
    List<HealthDataAccess>? permissions,
  }) async =>
      requestAuthorizationResult;
}

class _FakeHealthConnectLauncher implements HealthConnectLauncher {
  _FakeHealthConnectLauncher({
    this.openSettingsResult = true,
    this.openStoreResult = true,
  });

  final bool openSettingsResult;
  final bool openStoreResult;

  int settingsCalls = 0;
  int storeCalls = 0;

  @override
  Future<bool> openHealthConnectSettings() async {
    settingsCalls += 1;
    return openSettingsResult;
  }

  @override
  Future<bool> openHealthConnectStore() async {
    storeCalls += 1;
    return openStoreResult;
  }
}

HealthDataPoint _numericPoint({
  required HealthDataType type,
  required num value,
  required DateTime from,
  DateTime? to,
}) {
  return HealthDataPoint(
    uuid: '${type.name}-${from.millisecondsSinceEpoch}',
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
  test(
      'loadToday sets permissionDenied state when Health Connect access is denied',
      () async {
    final provider = BiometricsProvider(
      HealthConnectService(
        healthClient: _FakeHealthClient(requestAuthorizationResult: false),
        platformOverride: TargetPlatform.android,
        isWebOverride: false,
      ),
    );

    await provider.loadToday();

    expect(provider.state, BiometricsState.permissionDenied);
    expect(provider.primaryAction, BiometricsAction.openHealthConnectAccess);
  });

  test(
      'performPrimaryAction opens Health Connect settings without store fallback when access is denied',
      () async {
    final launcher = _FakeHealthConnectLauncher(openSettingsResult: false);
    final provider = BiometricsProvider(
      HealthConnectService(
        healthClient: _FakeHealthClient(requestAuthorizationResult: false),
        launcher: launcher,
        platformOverride: TargetPlatform.android,
        isWebOverride: false,
      ),
    );

    await provider.loadToday();
    await provider.performPrimaryAction();

    expect(provider.state, BiometricsState.permissionDenied);
    expect(launcher.settingsCalls, 1);
    expect(launcher.storeCalls, 0);
  });

  test('loadToday captures sync metadata for demo mode', () async {
    final provider = BiometricsProvider(
      HealthConnectService(
        platformOverride: TargetPlatform.iOS,
        isWebOverride: false,
      ),
    );

    await provider.loadToday();

    expect(provider.lastUpdatedAt, isNotNull);
    expect(provider.sourceLabel, 'Vitalis Demo');
    expect(provider.freshnessLabel, 'Demo');
  });

  test('loadToday syncs recent biometrics to cloud when API client is set',
      () async {
    final postedBodies = <String>[];
    final mockClient = MockClient((req) async {
      if (req.method == 'POST' && req.url.path.endsWith('/v1/biometrics')) {
        postedBodies.add(req.body);
        return http.Response('{"status":"ok"}', 201);
      }
      return http.Response('{}', 200);
    });
    final apiClient = ApiClient(
      baseUrl: 'https://example.test',
      apiKey: 'key',
      httpClient: mockClient,
    );
    final provider = BiometricsProvider(
      HealthConnectService(
        healthClient: _FakeHealthClient(
          hasGrantedPermissions: true,
          points: <HealthDataPoint>[
            _numericPoint(
              type: HealthDataType.STEPS,
              value: 8500,
              from: DateTime(2026, 4, 5, 8),
            ),
          ],
        ),
        platformOverride: TargetPlatform.android,
        isWebOverride: false,
      ),
      apiClient: apiClient,
      now: () => DateTime(2026, 4, 5, 12),
      syncWindowDays: 3,
    );

    await provider.loadToday();

    expect(provider.state, BiometricsState.live);
    expect(postedBodies, hasLength(3));
    expect(postedBodies[0], contains('"date":"2026-04-03"'));
    expect(postedBodies[1], contains('"date":"2026-04-04"'));
    expect(postedBodies[2], contains('"date":"2026-04-05"'));
  });

  test('loadToday stays live when cloud sync fails', () async {
    final mockClient = MockClient((req) async {
      if (req.method == 'POST' && req.url.path.endsWith('/v1/biometrics')) {
        return http.Response('{"error":"boom"}', 500);
      }
      return http.Response('{}', 200);
    });
    final apiClient = ApiClient(
      baseUrl: 'https://example.test',
      apiKey: 'key',
      httpClient: mockClient,
    );
    final provider = BiometricsProvider(
      HealthConnectService(
        healthClient: _FakeHealthClient(
          hasGrantedPermissions: true,
          points: <HealthDataPoint>[
            _numericPoint(
              type: HealthDataType.STEPS,
              value: 8500,
              from: DateTime(2026, 4, 5, 8),
            ),
          ],
        ),
        platformOverride: TargetPlatform.android,
        isWebOverride: false,
      ),
      apiClient: apiClient,
      now: () => DateTime(2026, 4, 5, 12),
      syncWindowDays: 1,
    );

    await provider.loadToday();

    expect(provider.state, BiometricsState.live);
    expect(provider.latest?.steps, 8500);
    expect(provider.statusMessage, contains('סנכרון'));
  });
}
