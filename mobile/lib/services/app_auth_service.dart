import 'package:flutter_appauth/flutter_appauth.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import 'auth_config.dart';
import 'auth_service.dart';

/// Real [AuthService] backed by AppAuth (OIDC authorization-code + PKCE)
/// against the Entra External ID tenant.
///
/// The refresh token is persisted in the platform secure store so the session
/// survives app restarts; the ID token is minted fresh on restore.
class AppAuthService implements AuthService {
  final FlutterAppAuth _appAuth;
  final FlutterSecureStorage _storage;

  static const _refreshKey = 'vitalis_refresh_token';

  AppAuthService({FlutterAppAuth? appAuth, FlutterSecureStorage? storage})
      : _appAuth = appAuth ?? const FlutterAppAuth(),
        _storage = storage ??
            const FlutterSecureStorage(
              // EncryptedSharedPreferences keeps the refresh token across app
              // restarts far more reliably than the legacy KeyStore wrapper.
              aOptions: AndroidOptions(encryptedSharedPreferences: true),
            );

  @override
  Future<String?> signIn() async {
    final result = await _appAuth.authorizeAndExchangeCode(
      AuthorizationTokenRequest(
        AuthConfig.clientId,
        AuthConfig.redirectUri,
        discoveryUrl: AuthConfig.discoveryUrl,
        scopes: AuthConfig.scopes,
      ),
    );
    if (result.refreshToken != null) {
      await _storage.write(key: _refreshKey, value: result.refreshToken);
    }
    return result.idToken;
  }

  @override
  Future<String?> restoreSession() async {
    final refresh = await _storage.read(key: _refreshKey);
    if (refresh == null) return null;
    try {
      final result = await _appAuth.token(
        TokenRequest(
          AuthConfig.clientId,
          AuthConfig.redirectUri,
          discoveryUrl: AuthConfig.discoveryUrl,
          refreshToken: refresh,
          scopes: AuthConfig.scopes,
        ),
      );
      if (result.refreshToken != null) {
        await _storage.write(key: _refreshKey, value: result.refreshToken);
      }
      return result.idToken;
    } catch (e) {
      if (_isInvalidGrant(e)) {
        // Refresh token genuinely expired/revoked — the session is over.
        await _storage.delete(key: _refreshKey);
        return null;
      }
      // Transient error (offline, server hiccup): keep the refresh token so a
      // later attempt can succeed, and signal "retryable" by rethrowing.
      rethrow;
    }
  }

  /// Whether [error] indicates the refresh token is no longer valid (as opposed
  /// to a transient network/server failure worth retrying).
  static bool _isInvalidGrant(Object error) {
    final s = error.toString().toLowerCase();
    return s.contains('invalid_grant') ||
        s.contains('invalid grant') ||
        s.contains('interaction_required') ||
        s.contains('token is not active') ||
        s.contains('expired or revoked') ||
        s.contains('aadsts70008') || // refresh token expired
        s.contains('aadsts700082'); // refresh token expired due to inactivity
  }

  @override
  Future<void> signOut() async {
    await _storage.delete(key: _refreshKey);
  }
}
