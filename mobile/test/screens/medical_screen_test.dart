import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:provider/provider.dart';

import 'package:vitalis/providers/medical_provider.dart';
import 'package:vitalis/screens/medical_screen.dart';
import 'package:vitalis/services/api_client.dart';
import 'package:vitalis/services/document_picker.dart';

class _FakeDocumentPicker implements DocumentPicker {
  @override
  Future<PickedDocument?> pickFromCamera() async => null;

  @override
  Future<PickedDocument?> pickFile() async => null;
}

void main() {
  group('MedicalScreen', () {
    Widget build(MockClient mock) {
      final api = ApiClient(baseUrl: 'http://test/api', apiKey: 'k', httpClient: mock);
      return MultiProvider(
        providers: [
          ChangeNotifierProvider(create: (_) => MedicalProvider(api)),
          Provider<DocumentPicker>(create: (_) => _FakeDocumentPicker()),
        ],
        child: const MaterialApp(home: MedicalScreen()),
      );
    }

    testWidgets('shows the title and empty state', (tester) async {
      await tester.pumpWidget(build(
        MockClient((req) async => http.Response(jsonEncode({'uploads': []}), 200)),
      ));
      await tester.pump(); // run initState microtask (start load)
      await tester.pump(const Duration(milliseconds: 50)); // finish load

      expect(find.text('מסמכים רפואיים'), findsWidgets);
      expect(find.textContaining('אין עדיין מסמכים'), findsOneWidget);
    });

    testWidgets('lists uploaded documents', (tester) async {
      await tester.pumpWidget(build(MockClient((req) async {
        return http.Response(
          jsonEncode({
            'uploads': [
              {
                'id': 'u1',
                'filename': 'labs.pdf',
                'content_type': 'application/pdf',
                'size_bytes': 2048,
                'uploaded_at': '2026-07-05T10:00:00',
                'extracted': false,
              },
            ],
          }),
          200,
        );
      })));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 50));

      expect(find.text('labs.pdf'), findsOneWidget);
    });
  });
}
