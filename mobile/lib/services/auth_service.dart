/// Abstraction over the platform SSO mechanism (Entra External ID via AppAuth).
///
/// Kept as an interface so [AuthProvider] can be unit-tested with a fake,
/// while the real implementation ([AppAuthService]) wraps `flutter_appauth`.
abstract class AuthService {
  /// Interactively sign in. Returns the ID token (JWT) on success, or null if
  /// the user cancelled.
  Future<String?> signIn();

  /// Silently restore a previous session using the stored refresh token.
  /// Returns a fresh ID token on success, `null` when the session is genuinely
  /// over (no refresh token, or it was expired/revoked), and throws on a
  /// transient failure worth retrying (e.g. the device is offline).
  Future<String?> restoreSession();

  /// Sign out and clear any stored tokens.
  Future<void> signOut();
}
