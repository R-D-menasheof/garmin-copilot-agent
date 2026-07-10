import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:vitalis/services/api_client.dart';

void main() {
  test('registerPushToken posts the token and platform', () async {
    late Map<String, dynamic> body;
    final api = ApiClient(
      baseUrl: 'http://test/api',
      apiKey: 'k',
      httpClient: MockClient((req) async {
        expect(req.url.path, endsWith('/v1/push/register'));
        body = jsonDecode(req.body) as Map<String, dynamic>;
        return http.Response('{"status":"ok"}', 201);
      }),
    );

    await api.registerPushToken('fcm-abc');

    expect(body['token'], 'fcm-abc');
    expect(body['platform'], 'android');
  });

  test('registerPushToken throws on error status', () async {
    final api = ApiClient(
      baseUrl: 'http://test/api',
      apiKey: 'k',
      httpClient: MockClient((req) async => http.Response('{"error":"x"}', 500)),
    );

    expect(() => api.registerPushToken('fcm-abc'), throwsA(isA<ApiException>()));
  });
}
