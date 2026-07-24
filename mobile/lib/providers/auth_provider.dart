import 'dart:async';

import 'package:flutter/foundation.dart';

import '../services/api_client.dart';
import '../services/auth_service.dart';

/// Authentication state for the app (Entra External ID SSO).
///
/// Wraps an [AuthService] for the platform sign-in mechanism and an
/// [ApiClient] to validate the token and fetch the user's identity via
/// `GET /v1/me`. On success it pushes the bearer token into the shared
/// [ApiClient] so every other provider's requests are authenticated, and
/// registers a refresher so the client can transparently recover from an
/// expired token on any request.
class AuthProvider extends ChangeNotifier {
  final ApiClient _api;
  final AuthService _auth;
  final Duration _retryBackoff;

  AuthProvider(this._api, this._auth, {Duration? retryBackoff})
      : _retryBackoff = retryBackoff ?? const Duration(milliseconds: 500) {
    // Let the client silently refresh + retry when a request returns 401.
    _api.setTokenRefresher(_refreshForApi);
  }

  String? _userId;
  String? get userId => _userId;

  String _displayName = '';
  String get displayName => _displayName;

  String _email = '';
  String get email => _email;

  bool _onboarded = false;
  bool get onboarded => _onboarded;

  bool get isAuthenticated => _userId != null;

  /// True until the first silent restore attempt completes on startup, so the
  /// UI can show a splash instead of flashing the login screen.
  bool _initializing = true;
  bool get initializing => _initializing;

  bool _busy = false;
  bool get busy => _busy;

  /// Last sign-in error (diagnostic — surfaced on the login screen).
  String? _lastError;
  String? get lastError => _lastError;

  /// Interactive sign-in. Returns true when authenticated.
  Future<bool> signIn() async {
    _busy = true;
    _lastError = null;
    notifyListeners();
    try {
      final token = await _auth.signIn();
      if (token == null) {
        _lastError = 'auth returned no token (cancelled or no id_token)';
        return false;
      }
      final ok = await _applyToken(token);
      if (!ok) _lastError ??= 'signed in but /v1/me failed (token rejected)';
      return ok;
    } catch (e) {
      _lastError = e.toString();
      return false;
    } finally {
      _busy = false;
      notifyListeners();
    }
  }

  /// Silently restore a previous session on startup. Returns true when
  /// authenticated. Always clears [initializing] when done.
  Future<bool> tryRestore() async {
    try {
      final token = await _auth.restoreSession();
      if (token == null) return false;
      return await _applyToken(token);
    } catch (_) {
      return false;
    } finally {
      _initializing = false;
      notifyListeners();
    }
  }

  /// Silently refresh the access token from the stored refresh token, without
  /// re-fetching identity. Best-effort — used on app resume to keep the token
  /// fresh. Returns true when a new token was applied.
  Future<bool> refreshToken() async {
    try {
      final token = await _auth.restoreSession();
      if (token == null) return false;
      _api.updateToken(token);
      return true;
    } catch (_) {
      return false;
    }
  }

  /// Refresher wired into [ApiClient]: invoked when a request returns 401.
  /// Refreshes the token; if the session is genuinely over it signs out so the
  /// router returns the user to the login screen (rather than a raw error).
  Future<bool> _refreshForApi() async {
    try {
      final token = await _auth.restoreSession();
      if (token != null) {
        _api.updateToken(token);
        return true;
      }
      // Genuine end of session (no/expired refresh token) → back to login.
      await signOut();
      return false;
    } catch (_) {
      // Transient failure — fail this request but keep the session alive.
      return false;
    }
  }

  /// Apply [token] and fetch identity, retrying transient failures (e.g. an
  /// Azure Functions cold start) a few times. A real 401/403 is not retried.
  Future<bool> _applyToken(String token) async {
    _api.updateToken(token);
    const maxAttempts = 3;
    for (var attempt = 0; attempt < maxAttempts; attempt++) {
      try {
        final me = await _api.getMe().timeout(const Duration(seconds: 25));
        _userId = me.userId;
        _displayName = me.displayName;
        _email = me.email;
        _onboarded = me.onboarded;
        notifyListeners();
        return true;
      } on ApiException catch (e) {
        // Token genuinely rejected — not retryable.
        if (e.statusCode == 401 || e.statusCode == 403) {
          _lastError = 'getMe rejected (${e.statusCode})';
          _api.clearToken();
          return false;
        }
        if (attempt == maxAttempts - 1) {
          _lastError = 'getMe failed after retries: $e';
          _api.clearToken();
          return false;
        }
      } on TimeoutException {
        if (attempt == maxAttempts - 1) {
          _lastError = 'getMe timed out (server waking up) — try again';
          _api.clearToken();
          return false;
        }
      } catch (e) {
        if (attempt == maxAttempts - 1) {
          _lastError = 'getMe failed: $e';
          _api.clearToken();
          return false;
        }
      }
      await Future<void>.delayed(_retryBackoff * (attempt + 1));
    }
    return false;
  }

  /// Reflect that onboarding completed (set after the wizard submits).
  void setOnboarded(bool value) {
    _onboarded = value;
    notifyListeners();
  }

  /// Update the user's display name, persist it to the profile, and reflect it
  /// locally so the account indicator updates immediately.
  Future<void> updateDisplayName(String name) async {
    await _api.patchProfile({'display_name': name});
    _displayName = name;
    notifyListeners();
  }

  Future<void> signOut() async {
    await _auth.signOut();
    _api.clearToken();
    _userId = null;
    _displayName = '';
    _email = '';
    _onboarded = false;
    notifyListeners();
  }
}
