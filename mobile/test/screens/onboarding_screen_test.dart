import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/testing.dart';
import 'package:http/http.dart' as http;
import 'package:provider/provider.dart';

import 'package:vitalis/providers/auth_provider.dart';
import 'package:vitalis/screens/onboarding_screen.dart';
import 'package:vitalis/services/api_client.dart';
import 'package:vitalis/services/auth_service.dart';

class _FakeAuth implements AuthService {
  @override
  Future<String?> signIn() async => 'jwt';
  @override
  Future<String?> restoreSession() async => 'jwt';
  @override
  Future<void> signOut() async {}
}

void main() {
  testWidgets('renders essential onboarding fields', (tester) async {
    final api = ApiClient(baseUrl: 'http://t/api', apiKey: 'k');
    final auth = AuthProvider(api, _FakeAuth());
    await tester.pumpWidget(_wrap(api, auth));

    expect(find.byKey(const ValueKey('onboard-height')), findsOneWidget);
    expect(find.byKey(const ValueKey('onboard-dob')), findsOneWidget);
    expect(find.byKey(const ValueKey('onboard-submit')), findsOneWidget);
  });

  testWidgets('submit PATCHes profile with onboarded=true and sets flag',
      (tester) async {
    Map<String, dynamic>? patched;
    final mock = MockClient((req) async {
      if (req.method == 'PATCH' && req.url.path.contains('/v1/profile')) {
        patched = jsonDecode(req.body) as Map<String, dynamic>;
        return http.Response(jsonEncode({'profile': patched}), 200);
      }
      return http.Response('{}', 200);
    });
    final api = ApiClient(baseUrl: 'http://t/api', apiKey: 'k', httpClient: mock);
    final auth = AuthProvider(api, _FakeAuth());

    await tester.pumpWidget(_wrap(api, auth));
    await tester.enterText(find.byKey(const ValueKey('onboard-height')), '183');
    await tester.tap(find.byKey(const ValueKey('onboard-submit')));
    await tester.pumpAndSettle();

    expect(patched, isNotNull);
    expect(patched!['onboarded'], true);
    expect(patched!['height_cm'], 183);
    expect(auth.onboarded, isTrue);
  });
}

Widget _wrap(ApiClient api, AuthProvider auth) => MultiProvider(
      providers: [
        Provider<ApiClient>.value(value: api),
        ChangeNotifierProvider<AuthProvider>.value(value: auth),
      ],
      child: const MaterialApp(
        locale: Locale('he'),
        home: OnboardingScreen(),
      ),
    );
