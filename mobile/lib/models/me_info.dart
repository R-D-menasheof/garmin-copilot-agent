/// Result of `GET /v1/me` — the authenticated user's identity + onboarding state.
class MeInfo {
  final String userId;
  final String displayName;
  final String email;
  final bool onboarded;

  const MeInfo({
    required this.userId,
    required this.displayName,
    required this.email,
    required this.onboarded,
  });

  factory MeInfo.fromJson(Map<String, dynamic> json) => MeInfo(
        userId: json['user_id'] as String? ?? '',
        displayName: json['display_name'] as String? ?? '',
        email: json['email'] as String? ?? '',
        onboarded: json['onboarded'] as bool? ?? false,
      );
}
