import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';

import 'package:vitalis/services/api_client.dart';

void main() {
  ApiClient client(MockClient mock) =>
      ApiClient(baseUrl: 'http://test/api', apiKey: 'k', httpClient: mock);

  group('ApiClient medical uploads', () {
    test('uploadMedicalDocument sends base64 content and returns metadata',
        () async {
      late Map<String, dynamic> sentBody;
      final mock = MockClient((req) async {
        expect(req.url.path, endsWith('/v1/medical/upload'));
        expect(req.headers['x-api-key'], 'k');
        sentBody = jsonDecode(req.body) as Map<String, dynamic>;
        return http.Response(
          jsonEncode({
            'status': 'ok',
            'upload': {
              'id': 'abc',
              'filename': 'labs.pdf',
              'content_type': 'application/pdf',
              'size_bytes': 3,
              'category': '',
              'note': '',
              'uploaded_at': '2026-07-05T10:00:00',
              'extracted': false,
            },
          }),
          201,
        );
      });

      final result = await client(mock).uploadMedicalDocument(
        bytes: Uint8List.fromList([1, 2, 3]),
        filename: 'labs.pdf',
        contentType: 'application/pdf',
      );

      expect(sentBody['filename'], 'labs.pdf');
      expect(sentBody['content_type'], 'application/pdf');
      expect(base64Decode(sentBody['content'] as String), [1, 2, 3]);
      expect(result.id, 'abc');
      expect(result.contentType, 'application/pdf');
    });

    test('getMedicalUploads parses the list', () async {
      final mock = MockClient((req) async {
        expect(req.url.path, endsWith('/v1/medical/uploads'));
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
      });

      final uploads = await client(mock).getMedicalUploads();
      expect(uploads, hasLength(1));
      expect(uploads.first.filename, 'a.pdf');
    });

    test('getMedicalUploads returns empty when key missing', () async {
      final mock = MockClient((req) async => http.Response(jsonEncode({}), 200));
      expect(await client(mock).getMedicalUploads(), isEmpty);
    });
  });
}
