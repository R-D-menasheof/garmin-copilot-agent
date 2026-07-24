import 'dart:async';

import 'package:http/http.dart' as http;

/// HTTP client that injects the auth header on every request and transparently
/// recovers from an expired token.
///
/// On a `401 Unauthorized` it invokes the registered [setRefresher] callback
/// once (shared across concurrent 401s), then retries the original request a
/// single time with the refreshed token. When authenticated it sends
/// `Authorization: Bearer <token>`; otherwise it falls back to the transitional
/// `x-api-key` header.
class AuthHttpClient extends http.BaseClient {
  AuthHttpClient(this._inner, {required this.apiKey});

  final http.Client _inner;
  final String apiKey;

  String? _bearerToken;
  Future<bool> Function()? _refresher;
  Future<bool>? _refreshInFlight;

  /// Use [token] as the bearer credential for subsequent requests.
  void updateToken(String token) => _bearerToken = token;

  /// Drop the bearer token, reverting to the `x-api-key` fallback.
  void clearToken() => _bearerToken = null;

  /// Register the callback used to refresh the token on a 401. It must update
  /// this client's token (via [updateToken]) and return true on success.
  void setRefresher(Future<bool> Function()? refresher) => _refresher = refresher;

  @override
  Future<http.StreamedResponse> send(http.BaseRequest request) async {
    final body = await request.finalize().toBytes();

    final first = await _inner.send(_build(request, body));
    if (first.statusCode != 401 || _refresher == null) return first;

    // Token likely expired — refresh once (shared across concurrent 401s) and
    // retry the request a single time.
    await first.stream.drain<void>();
    await (_refreshInFlight ??=
        _refresher!().whenComplete(() => _refreshInFlight = null));
    return _inner.send(_build(request, body));
  }

  http.Request _build(http.BaseRequest original, List<int> body) {
    final req = http.Request(original.method, original.url)
      ..followRedirects = original.followRedirects
      ..maxRedirects = original.maxRedirects
      ..persistentConnection = original.persistentConnection
      ..bodyBytes = body;
    original.headers.forEach((key, value) {
      final lower = key.toLowerCase();
      // Skip auth (re-applied below) and content-length (recomputed from body).
      if (lower != 'authorization' &&
          lower != 'x-api-key' &&
          lower != 'content-length') {
        req.headers[key] = value;
      }
    });
    final token = _bearerToken;
    if (token != null) {
      req.headers['Authorization'] = 'Bearer $token';
    } else if (apiKey.isNotEmpty) {
      req.headers['x-api-key'] = apiKey;
    }
    return req;
  }

  @override
  void close() => _inner.close();
}
