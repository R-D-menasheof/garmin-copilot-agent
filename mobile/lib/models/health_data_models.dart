class LabDataPoint {
  final DateTime date;
  final double value;
  final String unit;
  final String referenceRange;
  final String status; // normal, high, low

  const LabDataPoint({
    required this.date,
    required this.value,
    required this.unit,
    this.referenceRange = '',
    this.status = 'normal',
  });

  factory LabDataPoint.fromJson(Map<String, dynamic> json) => LabDataPoint(
        date: DateTime.parse(json['date'] as String),
        value: (json['value'] as num).toDouble(),
        unit: json['unit'] as String,
        referenceRange: (json['reference_range'] as String?) ?? '',
        status: (json['status'] as String?) ?? 'normal',
      );

  Map<String, dynamic> toJson() => {
        'date': date.toIso8601String().split('T').first,
        'value': value,
        'unit': unit,
        'reference_range': referenceRange,
        'status': status,
      };
}

class LabTrend {
  final String metric;
  final String displayNameHe;
  final List<LabDataPoint> values;

  const LabTrend({
    required this.metric,
    this.displayNameHe = '',
    this.values = const [],
  });

  factory LabTrend.fromJson(Map<String, dynamic> json) => LabTrend(
        metric: json['metric'] as String,
        displayNameHe: (json['display_name_he'] as String?) ?? '',
        values: (json['values'] as List? ?? [])
            .map((v) => LabDataPoint.fromJson(v as Map<String, dynamic>))
            .toList(),
      );

  Map<String, dynamic> toJson() => {
        'metric': metric,
        'display_name_he': displayNameHe,
        'values': values.map((v) => v.toJson()).toList(),
      };
}

class HealthCorrelation {
  final String metricA;
  final String metricB;
  final String relationship;
  final String descriptionHe;
  final String evidence;
  final double confidence;
  final DateTime discoveredDate;

  const HealthCorrelation({
    required this.metricA,
    required this.metricB,
    required this.relationship,
    required this.descriptionHe,
    required this.evidence,
    required this.confidence,
    required this.discoveredDate,
  });

  factory HealthCorrelation.fromJson(Map<String, dynamic> json) =>
      HealthCorrelation(
        metricA: json['metric_a'] as String,
        metricB: json['metric_b'] as String,
        relationship: json['relationship'] as String,
        descriptionHe: json['description_he'] as String,
        evidence: json['evidence'] as String,
        confidence: (json['confidence'] as num).toDouble(),
        discoveredDate: DateTime.parse(json['discovered_date'] as String),
      );

  Map<String, dynamic> toJson() => {
        'metric_a': metricA,
        'metric_b': metricB,
        'relationship': relationship,
        'description_he': descriptionHe,
        'evidence': evidence,
        'confidence': confidence,
        'discovered_date': discoveredDate.toIso8601String().split('T').first,
      };
}
