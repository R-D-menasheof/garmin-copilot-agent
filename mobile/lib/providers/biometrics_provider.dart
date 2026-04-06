import 'package:flutter/foundation.dart';

import '../models/biometrics_record.dart';
import '../services/api_client.dart';
import '../services/health_connect.dart';

enum BiometricsState {
  idle,
  live,
  demo,
  permissionDenied,
  unavailable,
  error,
}

enum BiometricsAction {
  retry,
  openHealthConnectAccess,
  openHealthConnectStore,
}

/// State management for latest biometrics data.
class BiometricsProvider extends ChangeNotifier {
  final HealthConnectService _healthConnect;
  final ApiClient? _apiClient;
  final DateTime Function() _now;
  final int _syncWindowDays;

  BiometricsRecord? _latest;
  BiometricsRecord? get latest => _latest;

  bool _loading = false;
  bool get loading => _loading;

  bool _permissionGranted = false;
  bool get permissionGranted => _permissionGranted;

  BiometricsState _state = BiometricsState.idle;
  BiometricsState get state => _state;

  BiometricsAction? _primaryAction;
  BiometricsAction? get primaryAction => _primaryAction;

  String? _statusMessage;
  String? get statusMessage => _statusMessage;

  DateTime? _lastUpdatedAt;
  DateTime? get lastUpdatedAt => _lastUpdatedAt;

  HealthConnectAvailability _availability =
      HealthConnectAvailability.unsupportedPlatform;
  HealthConnectAvailability get availability => _availability;

  /// Whether Health Connect is available on this platform.
  bool get isAvailable => _availability == HealthConnectAvailability.available;

  bool get usesDemoData => _state == BiometricsState.demo;

  String get sourceLabel {
    if (usesDemoData) {
      return 'Vitalis Demo';
    }
    return 'Health Connect';
  }

  String get freshnessLabel {
    switch (_state) {
      case BiometricsState.live:
        return 'Live';
      case BiometricsState.demo:
        return 'Demo';
      case BiometricsState.permissionDenied:
        return 'Needs access';
      case BiometricsState.unavailable:
        return 'Unavailable';
      case BiometricsState.error:
        return 'Error';
      case BiometricsState.idle:
        return 'Idle';
    }
  }

  String get lastUpdatedLabel {
    final timestamp = _lastUpdatedAt;
    if (timestamp == null) {
      return 'טרם בוצע';
    }
    final date = '${timestamp.year}-${timestamp.month.toString().padLeft(2, '0')}-${timestamp.day.toString().padLeft(2, '0')}';
    final time = '${timestamp.hour.toString().padLeft(2, '0')}:${timestamp.minute.toString().padLeft(2, '0')}';
    return '$date $time';
  }

  String? get primaryActionLabel {
    switch (_primaryAction) {
      case BiometricsAction.retry:
        return 'נסה שוב';
      case BiometricsAction.openHealthConnectAccess:
        return 'תן גישה';
      case BiometricsAction.openHealthConnectStore:
        if (_availability == HealthConnectAvailability.updateRequired) {
          return 'עדכן Health Connect';
        }
        return 'התקן Health Connect';
      case null:
        return null;
    }
  }

  BiometricsProvider(
    this._healthConnect, {
    ApiClient? apiClient,
    DateTime Function()? now,
    int syncWindowDays = 7,
  })  : _apiClient = apiClient,
        _now = now ?? DateTime.now,
        _syncWindowDays = syncWindowDays;

  /// Request Health Connect permissions and load today's data.
  Future<void> init() async {
    await loadToday();
  }

  /// Load today's biometrics from Health Connect.
  Future<void> loadToday() async {
    _loading = true;
    notifyListeners();
    try {
      _availability = await _healthConnect.getAvailability();
      if (_availability == HealthConnectAvailability.unsupportedPlatform) {
        _latest = await _healthConnect.readToday();
        _state = BiometricsState.demo;
        _primaryAction = null;
        _statusMessage =
            'מצב הדגמה. נתונים אמיתיים זמינים רק באנדרואיד דרך Health Connect.';
        _lastUpdatedAt = DateTime.now();
        return;
      }

      if (_availability == HealthConnectAvailability.updateRequired) {
        _latest = null;
        _permissionGranted = false;
        _state = BiometricsState.unavailable;
        _primaryAction = BiometricsAction.openHealthConnectStore;
        _statusMessage = 'צריך לעדכן את Health Connect במכשיר.';
        return;
      }

      if (_availability == HealthConnectAvailability.unavailable) {
        _latest = null;
        _permissionGranted = false;
        _state = BiometricsState.unavailable;
        _primaryAction = BiometricsAction.openHealthConnectStore;
        _statusMessage = 'Health Connect לא זמין או לא מותקן במכשיר.';
        return;
      }

      _permissionGranted = await _healthConnect.requestPermissions();
      if (!_permissionGranted) {
        _latest = null;
        _state = BiometricsState.permissionDenied;
        _primaryAction = BiometricsAction.openHealthConnectAccess;
        _statusMessage = 'צריך לאשר גישה ל-Health Connect כדי לקרוא נתונים.';
        return;
      }

      final today = _now();
      _latest = await _healthConnect.readDay(today);
      _state = BiometricsState.live;
      _primaryAction = null;
      _statusMessage = null;
      _lastUpdatedAt = today;

      try {
        await _syncRecentBiometrics(endDate: today);
      } catch (e) {
        _statusMessage = 'הנתונים נטענו אבל סנכרון לענן נכשל: $e';
      }
    } catch (e) {
      _state = BiometricsState.error;
      _primaryAction = BiometricsAction.retry;
      _statusMessage = 'קריאת נתוני Health Connect נכשלה: $e';
    } finally {
      _loading = false;
      notifyListeners();
    }
  }

  Future<void> performPrimaryAction() async {
    switch (_primaryAction) {
      case BiometricsAction.retry:
        await loadToday();
        return;
      case BiometricsAction.openHealthConnectAccess:
        final granted = await _healthConnect.requestPermissions();
        if (granted) {
          await loadToday();
          return;
        }
        await _healthConnect.openHealthConnectSettings();
        return;
      case BiometricsAction.openHealthConnectStore:
        final openedStore = await _healthConnect.openHealthConnectStore();
        if (!openedStore) {
          await _healthConnect.openHealthConnectSettings();
        }
        return;
      case null:
        return;
    }
  }

  /// Manually update biometrics (e.g., from API sync).
  void update(BiometricsRecord record) {
    _latest = record;
    _lastUpdatedAt = DateTime.now();
    notifyListeners();
  }

  Future<void> _syncRecentBiometrics({required DateTime endDate}) async {
    final apiClient = _apiClient;
    if (apiClient == null ||
        _availability != HealthConnectAvailability.available ||
        _syncWindowDays <= 0) {
      return;
    }

    final normalizedEnd = DateTime(endDate.year, endDate.month, endDate.day);
    final normalizedLatest = _latest?.date;

    for (var offset = _syncWindowDays - 1; offset >= 0; offset -= 1) {
      final day = normalizedEnd.subtract(Duration(days: offset));
      final record = normalizedLatest != null &&
              normalizedLatest.year == day.year &&
              normalizedLatest.month == day.month &&
              normalizedLatest.day == day.day
          ? _latest!
          : await _healthConnect.readDay(day);
      await apiClient.postBiometrics(record);
    }
  }

  // ── Computed helpers for UI ───────────────────────────

  // Heart
  String get restingHrFormatted =>
      _latest?.restingHr != null ? '${_latest!.restingHr}' : '--';
  String get avgHrFormatted =>
      _latest?.avgHr != null ? '${_latest!.avgHr}' : '--';
  String get maxHrFormatted =>
      _latest?.maxHr != null ? '${_latest!.maxHr}' : '--';
  String get hrvFormatted =>
      _latest?.hrvMs != null ? '${_latest!.hrvMs}' : '--';

  // Vitals
  String get spo2Formatted => _latest?.spo2Pct != null
      ? '${_latest!.spo2Pct!.toStringAsFixed(0)}'
      : '--';
  String get bodyTempFormatted => _latest?.bodyTempC != null
      ? '${_latest!.bodyTempC!.toStringAsFixed(1)}°'
      : '--';
  String get respRateFormatted => _latest?.respiratoryRate != null
      ? '${_latest!.respiratoryRate!.toStringAsFixed(0)}'
      : '--';
  String get bpFormatted {
    if (_latest?.bpSystolic == null) return '--';
    return '${_latest!.bpSystolic}/${_latest!.bpDiastolic ?? "?"}';
  }

  // Activity
  String get stepsFormatted => _latest?.steps?.toString() ?? '--';
  String get activeCalFormatted => _latest?.activeCalories?.toString() ?? '--';
  String get totalCalFormatted => _latest?.totalCalories?.toString() ?? '--';
  String get floorsFormatted => _latest?.floorsClimbed?.toString() ?? '--';
  String get distanceFormatted {
    final m = _latest?.distanceMeters;
    if (m == null) return '--';
    return '${(m / 1000).toStringAsFixed(1)} km';
  }

  String get exerciseMinFormatted =>
      _latest?.exerciseMinutes?.toString() ?? '--';
  String get intensityMinFormatted =>
      _latest?.intensityMinutes?.toString() ?? '--';

  // Sleep
  String get sleepFormatted {
    final sec = _latest?.sleepSeconds;
    if (sec == null) return '--';
    final hours = sec ~/ 3600;
    final minutes = (sec % 3600) ~/ 60;
    return '${hours}h ${minutes}m';
  }

  String get deepSleepFormatted => _formatSleepStage(_latest?.deepSleepSeconds);
  String get lightSleepFormatted =>
      _formatSleepStage(_latest?.lightSleepSeconds);
  String get remSleepFormatted => _formatSleepStage(_latest?.remSleepSeconds);
  String get awakeSleepFormatted =>
      _formatSleepStage(_latest?.awakeSleepSeconds);
  String get sleepScoreFormatted => _latest?.sleepScore?.toString() ?? '--';

  // Body
  String get weightFormatted => _latest?.weightKg != null
      ? '${_latest!.weightKg!.toStringAsFixed(1)}'
      : '--';
  String get bodyFatFormatted => _latest?.bodyFatPct != null
      ? '${_latest!.bodyFatPct!.toStringAsFixed(1)}%'
      : '--';
  String get bmiFormatted =>
      _latest?.bmi != null ? '${_latest!.bmi!.toStringAsFixed(1)}' : '--';
  String get bmrFormatted => _latest?.basalMetabolicRate != null
      ? '${_latest!.basalMetabolicRate!.toStringAsFixed(0)}'
      : '--';

  // Hydration
  String get waterFormatted {
    final ml = _latest?.waterMl;
    if (ml == null) return '--';
    return ml >= 1000
        ? '${(ml / 1000).toStringAsFixed(1)} L'
        : '${ml.toStringAsFixed(0)} ml';
  }

  String _formatSleepStage(int? seconds) {
    if (seconds == null) return '--';
    final h = seconds ~/ 3600;
    final m = (seconds % 3600) ~/ 60;
    return h > 0 ? '${h}h ${m}m' : '${m}m';
  }
}
