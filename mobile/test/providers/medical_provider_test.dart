import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:vitalis/providers/medical_provider.dart';
import 'package:vitalis/services/api_client.dart';
import 'package:vitalis/services/document_picker.dart';

ApiClient _client(MockClient mock) =>
    ApiClient(baseUrl: 'http://test/api', apiKey: 'k', httpClient: mock);

PickedDocument _doc() => PickedDocument(
      bytes: Uint8List.fromList([1, 2, 3]),
      filename: 'x.pdf',
      contentType: 'application/pdf',
    );

void main() {
  group('MedicalProvider', () {
    test('loadDocuments populates the list', () async {
      final provider = MedicalProvider(_client(MockClient((req) async {
        return http.Response(
          jsonEncode({
            'uploads': [
              {
                'id': 'u1',
                'filename': 'a.pdf',
                'content_type': 'application/pdf',
                'size_bytes': 1,
                'uploaded_at': '2026-07-05T10:00:00',
                'extracted': false,
              },
            ],
          }),
          200,
        );
      })));

      await provider.loadDocuments();

      expect(provider.documents, hasLength(1));
      expect(provider.loading, false);
      expect(provider.error, isNull);
    });

    test('loadDocuments sets error on failure', () async {
      final provider = MedicalProvider(_client(
        MockClient((req) async => http.Response('{"error":"boom"}', 500)),
      ));

      await provider.loadDocuments();

      expect(provider.documents, isEmpty);
      expect(provider.error, isNotNull);
      expect(provider.loading, false);
    });

    test('uploadDocument prepends the new document on success', () async {
      final provider = MedicalProvider(_client(MockClient((req) async {
        return http.Response(
          jsonEncode({
            'status': 'ok',
            'upload': {
              'id': 'new',
              'filename': 'x.pdf',
              'content_type': 'application/pdf',
              'size_bytes': 3,
              'uploaded_at': '2026-07-05T10:00:00',
              'extracted': false,
            },
          }),
          201,
        );
      })));

      final ok = await provider.uploadDocument(_doc());

      expect(ok, true);
      expect(provider.documents.first.id, 'new');
      expect(provider.uploading, false);
    });

    test('uploadDocument returns false and sets error on failure', () async {
      final provider = MedicalProvider(_client(
        MockClient((req) async => http.Response('{"error":"bad"}', 400)),
      ));

      final ok = await provider.uploadDocument(_doc());

      expect(ok, false);
      expect(provider.error, isNotNull);
      expect(provider.uploading, false);
    });
  });
}
