/// Result of `GET /v1/medical/uploads` items and `POST /v1/medical/upload` —
/// metadata for a user-uploaded medical document (Phase 4b).
///
/// The raw file bytes live server-side; this is only the index metadata the
/// app shows in the documents list.
class MedicalUpload {
  final String id;
  final String filename;
  final String contentType;
  final int sizeBytes;
  final String category;
  final String note;
  final DateTime uploadedAt;
  final bool extracted;

  const MedicalUpload({
    required this.id,
    required this.filename,
    required this.contentType,
    required this.sizeBytes,
    this.category = '',
    this.note = '',
    required this.uploadedAt,
    this.extracted = false,
  });

  factory MedicalUpload.fromJson(Map<String, dynamic> json) => MedicalUpload(
        id: json['id'] as String,
        filename: json['filename'] as String,
        contentType: (json['content_type'] as String?) ?? '',
        sizeBytes: (json['size_bytes'] as num?)?.toInt() ?? 0,
        category: (json['category'] as String?) ?? '',
        note: (json['note'] as String?) ?? '',
        uploadedAt: DateTime.parse(json['uploaded_at'] as String),
        extracted: (json['extracted'] as bool?) ?? false,
      );

  Map<String, dynamic> toJson() => {
        'id': id,
        'filename': filename,
        'content_type': contentType,
        'size_bytes': sizeBytes,
        'category': category,
        'note': note,
        'uploaded_at': uploadedAt.toIso8601String(),
        'extracted': extracted,
      };
}
