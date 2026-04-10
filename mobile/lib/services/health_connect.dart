import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:health/health.dart';

import '../models/biometrics_record.dart';

enum HealthConnectAvailability {
  unsupportedPlatform,
  unavailable,
  updateRequired,
  available,
}

abstract class HealthConnectLauncher {
  Future<bool> openHealthConnectSettings();

  Future<bool> openHealthConnectStore();
}

class PlatformHealthConnectLauncher implements HealthConnectLauncher {
  static const MethodChannel _channel = MethodChannel('vitalis/health_connect');

  @override
  Future<bool> openHealthConnectSettings() async {
    try {
      return await _channel.invokeMethod<bool>('openHealthConnectSettings') ??
          false;
    } on PlatformException {
      return false;
    }
  }

  @override
  Future<bool> openHealthConnectStore() async {
    try {
      return await _channel.invokeMethod<bool>('openHealthConnectStore') ??
          false;
    } on PlatformException {
      return false;
    }
  }
}

abstract class HealthClient {
  Future<void> configure({bool useHealthConnectIfAvailable = false});

  Future<HealthConnectSdkStatus?> getHealthConnectSdkStatus();

  Future<bool?> hasPermissions(
    List<HealthDataType> types, {
    List<HealthDataAccess>? permissions,
  });

  Future<bool> requestAuthorization(
    List<HealthDataType> types, {
    List<HealthDataAccess>? permissions,
  });

  Future<List<HealthDataPoint>> getHealthDataFromTypes({
    required List<HealthDataType> types,
    required DateTime startTime,
    required DateTime endTime,
    bool includeManualEntry,
  });
}

class PluginHealthClient implements HealthClient {
  PluginHealthClient({Health? health}) : _health = health ?? Health();

  final Health _health;

  @override
  Future<void> configure({bool useHealthConnectIfAvailable = false}) {
    return _health.configure();
  }

  @override
  Future<HealthConnectSdkStatus?> getHealthConnectSdkStatus() {
    return _health.getHealthConnectSdkStatus();
  }

  @override
  Future<List<HealthDataPoint>> getHealthDataFromTypes({
    required List<HealthDataType> types,
    required DateTime startTime,
    required DateTime endTime,
    bool includeManualEntry = true,
  }) {
    return _health.getHealthDataFromTypes(
      types: types,
      startTime: startTime,
      endTime: endTime,
      recordingMethodsToFilter:
          includeManualEntry ? const [] : const [RecordingMethod.manual],
    );
  }

  @override
  Future<bool?> hasPermissions(
    List<HealthDataType> types, {
    List<HealthDataAccess>? permissions,
  }) {
    return _health.hasPermissions(types, permissions: permissions);
  }

  @override
  Future<bool> requestAuthorization(
    List<HealthDataType> types, {
    List<HealthDataAccess>? permissions,
  }) {
    return _health.requestAuthorization(types, permissions: permissions);
  }
}

/// Health Connect service — reads wearable data from Android Health Connect.
///
/// On web/desktop or when Health Connect is unavailable, returns demo data
/// so the app can still be previewed.
class HealthConnectService {
  HealthConnectService({
    HealthClient? healthClient,
    HealthConnectLauncher? launcher,
    TargetPlatform? platformOverride,
    bool? isWebOverride,
  })  : _healthClient = healthClient ?? PluginHealthClient(),
        _launcher = launcher ?? PlatformHealthConnectLauncher(),
        _platformOverride = platformOverride,
        _isWebOverride = isWebOverride;

  static const List<HealthDataType> _types = <HealthDataType>[
    HealthDataType.RESTING_HEART_RATE,
    HealthDataType.HEART_RATE,
    HealthDataType.BLOOD_OXYGEN,
    HealthDataType.BODY_TEMPERATURE,
    HealthDataType.RESPIRATORY_RATE,
    HealthDataType.BLOOD_PRESSURE_SYSTOLIC,
    HealthDataType.BLOOD_PRESSURE_DIASTOLIC,
    HealthDataType.STEPS,
    HealthDataType.ACTIVE_ENERGY_BURNED,
    HealthDataType.TOTAL_CALORIES_BURNED,
    HealthDataType.FLIGHTS_CLIMBED,
    HealthDataType.DISTANCE_DELTA,
    HealthDataType.SLEEP_SESSION,
    HealthDataType.SLEEP_DEEP,
    HealthDataType.SLEEP_LIGHT,
    HealthDataType.SLEEP_REM,
    HealthDataType.SLEEP_AWAKE,
    HealthDataType.WEIGHT,
    HealthDataType.HEIGHT,
    HealthDataType.BODY_FAT_PERCENTAGE,
    HealthDataType.BASAL_ENERGY_BURNED,
    HealthDataType.WATER,
  ];

  static final List<HealthDataAccess> _permissions =
      List<HealthDataAccess>.filled(_types.length, HealthDataAccess.READ);

  final HealthClient _healthClient;
  final HealthConnectLauncher _launcher;
  final TargetPlatform? _platformOverride;
  final bool? _isWebOverride;

  /// Whether Health Connect is supported on this platform.
  bool get isAvailable => !_isWeb && _platform == TargetPlatform.android;

  bool get _isWeb => _isWebOverride ?? kIsWeb;

  TargetPlatform get _platform => _platformOverride ?? defaultTargetPlatform;

  Future<HealthConnectAvailability> getAvailability() async {
    if (!isAvailable) {
      return HealthConnectAvailability.unsupportedPlatform;
    }

    try {
      await _healthClient.configure(useHealthConnectIfAvailable: true);
      final status = await _healthClient.getHealthConnectSdkStatus();
      switch (status) {
        case HealthConnectSdkStatus.sdkAvailable:
          return HealthConnectAvailability.available;
        case HealthConnectSdkStatus.sdkUnavailableProviderUpdateRequired:
          return HealthConnectAvailability.updateRequired;
        case HealthConnectSdkStatus.sdkUnavailable:
        case null:
          return HealthConnectAvailability.unavailable;
      }
    } catch (_) {
      return HealthConnectAvailability.unavailable;
    }
  }

  /// Request Health Connect permissions.
  /// Returns true if granted (or if on web/desktop demo mode).
  Future<bool> requestPermissions() async {
    if (!isAvailable) {
      return true;
    }

    final availability = await getAvailability();
    if (availability != HealthConnectAvailability.available) {
      return false;
    }

    final hasPermissions = await _healthClient.hasPermissions(
      _types,
      permissions: _permissions,
    );
    if (hasPermissions == true) {
      return true;
    }

    return _healthClient.requestAuthorization(
      _types,
      permissions: _permissions,
    );
  }

  Future<bool> openHealthConnectSettings() async {
    if (!isAvailable) {
      return false;
    }
    return _launcher.openHealthConnectSettings();
  }

  Future<bool> openHealthConnectStore() async {
    if (!isAvailable) {
      return false;
    }
    return _launcher.openHealthConnectStore();
  }

  /// Read today's biometrics from Health Connect.
  Future<BiometricsRecord> readToday() {
    return readDay(DateTime.now());
  }

  /// Read biometrics for a specific date.
  Future<BiometricsRecord> readDay(DateTime date) async {
    if (!isAvailable) {
      return _demoData(date: date);
    }

    await _healthClient.configure(useHealthConnectIfAvailable: true);
    final start = DateTime(date.year, date.month, date.day);
    final end = start.add(const Duration(days: 1));
    final points = await _healthClient.getHealthDataFromTypes(
      types: _types,
      startTime: start,
      endTime: end,
    );

    return _aggregate(points, date);
  }

  BiometricsRecord _aggregate(List<HealthDataPoint> points, DateTime date) {
    final restingHeartRates =
        _numericValues(points, HealthDataType.RESTING_HEART_RATE);
    final heartRates = _numericValues(points, HealthDataType.HEART_RATE);
    final steps = _sumValues(points, HealthDataType.STEPS)?.round();
    final activeCalories =
        _sumValues(points, HealthDataType.ACTIVE_ENERGY_BURNED)?.round();
    final totalCalories =
        _sumValues(points, HealthDataType.TOTAL_CALORIES_BURNED)?.round();
    final floorsClimbed =
        _sumValues(points, HealthDataType.FLIGHTS_CLIMBED)?.round();
    final distanceMeters = _sumValues(points, HealthDataType.DISTANCE_DELTA);
    final moveMinutes = null; // EXERCISE_TIME is iOS-only; unavailable on Android
    final sleepSeconds = _durationSeconds(points, HealthDataType.SLEEP_SESSION);
    final deepSleepSeconds =
        _durationSeconds(points, HealthDataType.SLEEP_DEEP);
    final lightSleepSeconds =
        _durationSeconds(points, HealthDataType.SLEEP_LIGHT);
    final remSleepSeconds = _durationSeconds(points, HealthDataType.SLEEP_REM);
    final awakeSleepSeconds =
        _durationSeconds(points, HealthDataType.SLEEP_AWAKE);
    final weightKg = _latestValue(points, HealthDataType.WEIGHT);
    final heightMeters = _latestValue(points, HealthDataType.HEIGHT);
    final bodyFatPct = _latestValue(points, HealthDataType.BODY_FAT_PERCENTAGE);
    final waterLiters = _sumValues(points, HealthDataType.WATER);

    return BiometricsRecord(
      date: date,
      restingHr: restingHeartRates.isNotEmpty
          ? restingHeartRates.last.round()
          : _minimumValue(heartRates)?.round(),
      avgHr: _averageValue(heartRates)?.round(),
      maxHr: _maximumValue(heartRates)?.round(),
      hrvMs: null,
      spo2Pct: _latestValue(points, HealthDataType.BLOOD_OXYGEN),
      bodyTempC: _latestValue(points, HealthDataType.BODY_TEMPERATURE),
      respiratoryRate: _latestValue(points, HealthDataType.RESPIRATORY_RATE),
      bpSystolic:
          _latestValue(points, HealthDataType.BLOOD_PRESSURE_SYSTOLIC)?.round(),
      bpDiastolic: _latestValue(points, HealthDataType.BLOOD_PRESSURE_DIASTOLIC)
          ?.round(),
      steps: steps,
      activeCalories: activeCalories,
      totalCalories: totalCalories,
      floorsClimbed: floorsClimbed,
      distanceMeters: distanceMeters,
      exerciseMinutes: moveMinutes,
      intensityMinutes: null,
      sleepSeconds: sleepSeconds,
      deepSleepSeconds: deepSleepSeconds,
      lightSleepSeconds: lightSleepSeconds,
      remSleepSeconds: remSleepSeconds,
      awakeSleepSeconds: awakeSleepSeconds,
      sleepScore: null,
      weightKg: weightKg,
      bodyFatPct: bodyFatPct,
      bmi: _calculateBmi(weightKg, heightMeters),
      basalMetabolicRate:
          _sumValues(points, HealthDataType.BASAL_ENERGY_BURNED),
      waterMl: waterLiters != null ? waterLiters * 1000 : null,
    );
  }

  List<double> _numericValues(
      List<HealthDataPoint> points, HealthDataType type) {
    return points
        .where(
            (point) => point.type == type && point.value is NumericHealthValue)
        .map((point) =>
            (point.value as NumericHealthValue).numericValue.toDouble())
        .toList();
  }

  double? _sumValues(List<HealthDataPoint> points, HealthDataType type) {
    final values = _numericValues(points, type);
    if (values.isEmpty) {
      return null;
    }
    return values.reduce((sum, value) => sum + value);
  }

  double? _latestValue(List<HealthDataPoint> points, HealthDataType type) {
    final filtered = points
        .where(
            (point) => point.type == type && point.value is NumericHealthValue)
        .toList()
      ..sort((a, b) => a.dateTo.compareTo(b.dateTo));
    if (filtered.isEmpty) {
      return null;
    }
    return (filtered.last.value as NumericHealthValue).numericValue.toDouble();
  }

  double? _averageValue(List<double> values) {
    if (values.isEmpty) {
      return null;
    }
    return values.reduce((sum, value) => sum + value) / values.length;
  }

  double? _minimumValue(List<double> values) {
    if (values.isEmpty) {
      return null;
    }
    return values.reduce((a, b) => a < b ? a : b);
  }

  double? _maximumValue(List<double> values) {
    if (values.isEmpty) {
      return null;
    }
    return values.reduce((a, b) => a > b ? a : b);
  }

  int? _durationSeconds(List<HealthDataPoint> points, HealthDataType type) {
    final durations = points
        .where((point) => point.type == type)
        .map((point) => point.dateTo.difference(point.dateFrom).inSeconds)
        .where((duration) => duration > 0)
        .toList();
    if (durations.isEmpty) {
      return null;
    }
    return durations.reduce((sum, value) => sum + value);
  }

  double? _calculateBmi(double? weightKg, double? heightMeters) {
    if (weightKg == null || heightMeters == null || heightMeters == 0) {
      return null;
    }
    return weightKg / (heightMeters * heightMeters);
  }

  /// Generate deterministic demo data for non-Android preview environments.
  BiometricsRecord _demoData({DateTime? date}) {
    final now = date ?? DateTime.now();

    return BiometricsRecord(
      date: now,
      restingHr: 64,
      avgHr: 74,
      maxHr: 132,
      hrvMs: null,
      spo2Pct: 97,
      bodyTempC: 36.6,
      respiratoryRate: 15,
      bpSystolic: null,
      bpDiastolic: null,
      steps: 8200,
      activeCalories: 410,
      totalCalories: 2580,
      floorsClimbed: 6,
      distanceMeters: 6100,
      exerciseMinutes: 42,
      intensityMinutes: null,
      sleepSeconds: 25200,
      deepSleepSeconds: 3600,
      lightSleepSeconds: 12600,
      remSleepSeconds: 5400,
      awakeSleepSeconds: 3600,
      sleepScore: null,
      weightKg: 111.8,
      bodyFatPct: null,
      bmi: null,
      basalMetabolicRate: 2140,
      waterMl: 1650,
    );
  }
}
