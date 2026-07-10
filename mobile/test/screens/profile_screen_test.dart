import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:provider/provider.dart';

import 'package:vitalis/providers/profile_provider.dart';
import 'package:vitalis/screens/profile_screen.dart';
import 'package:vitalis/services/api_client.dart';

void main() {
  group('ProfileScreen', () {
    Widget build(MockClient mock) {
      final api = ApiClient(baseUrl: 'http://test/api', apiKey: 'k', httpClient: mock);
      return ChangeNotifierProvider(
        create: (_) => ProfileProvider(api),
        child: const MaterialApp(home: ProfileScreen()),
      );
    }

    MockClient mock({
      Map<String, dynamic>? profile,
      void Function(http.Request req)? onPatch,
    }) {
      return MockClient((req) async {
        if (req.method == 'PATCH') {
          onPatch?.call(req);
          return http.Response(
            jsonEncode({'profile': profile ?? {}}),
            200,
            headers: {'content-type': 'application/json; charset=utf-8'},
          );
        }
        return http.Response(
          jsonEncode({'profile': profile ?? {}}),
          200,
          headers: {'content-type': 'application/json; charset=utf-8'},
        );
      });
    }

    testWidgets('renders editable fields and read-only wearable data',
        (tester) async {
      await tester.pumpWidget(build(mock(profile: {
        'display_name': 'רועי',
        'height_cm': 183.0,
        'weight_kg': 106.3,
        'goals': ['ירידה במשקל'],
      })));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 50));

      expect(find.text('הפרופיל שלי'), findsOneWidget);
      expect(find.text('פרטים אישיים'), findsOneWidget);
      expect(find.widgetWithText(TextField, 'רועי'), findsOneWidget);

      // The read-only wearable weight is near the bottom — scroll to it.
      await tester.scrollUntilVisible(
        find.text('106.3 ק"ג'),
        400,
        scrollable: find.byType(Scrollable).first,
      );
      expect(find.text('106.3 ק"ג'), findsOneWidget);
    });

    testWidgets('editing the name and saving PATCHes the change',
        (tester) async {
      String? patchedName;
      await tester.pumpWidget(build(mock(
        profile: {'display_name': 'רועי'},
        onPatch: (req) {
          final body = jsonDecode(req.body) as Map<String, dynamic>;
          patchedName = body['display_name'] as String?;
        },
      )));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 50));

      await tester.enterText(
          find.widgetWithText(TextField, 'רועי'), 'רועי חדש');
      await tester.tap(find.widgetWithText(FloatingActionButton, 'שמור'));
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 50));

      expect(patchedName, 'רועי חדש');
    });
  });
}
