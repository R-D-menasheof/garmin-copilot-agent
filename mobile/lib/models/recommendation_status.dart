import 'dart:convert';
import 'package:crypto/crypto.dart';

enum RecStatus {
  pending,
  done,
  snoozed;

  static RecStatus fromString(String value) {
    return RecStatus.values.firstWhere((e) => e.name == value);
  }
}

class RecommendationStatus {
  final String recId;
  final RecStatus status;
  final DateTime updatedAt;

  const RecommendationStatus({
    required this.recId,
    required this.status,
    required this.updatedAt,
  });

  factory RecommendationStatus.fromJson(Map<String, dynamic> json) =>
      RecommendationStatus(
        recId: json['rec_id'] as String,
        status: RecStatus.fromString(json['status'] as String),
        updatedAt: DateTime.parse(json['updated_at'] as String),
      );

  Map<String, dynamic> toJson() => {
        'rec_id': recId,
        'status': status.name,
        'updated_at': updatedAt.toIso8601String(),
      };

  /// Generate a stable ID from category+title (matches Python SHA-256[:16]).
  static String generateId(String category, String title) {
    final key = '$category:$title';
    final hash = sha256.convert(utf8.encode(key));
    return hash.toString().substring(0, 16);
  }

  RecommendationStatus copyWith({RecStatus? status, DateTime? updatedAt}) =>
      RecommendationStatus(
        recId: recId,
        status: status ?? this.status,
        updatedAt: updatedAt ?? this.updatedAt,
      );
}
