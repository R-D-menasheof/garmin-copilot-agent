import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';

import 'package:vitalis/providers/auth_provider.dart';
import 'package:vitalis/screens/login_screen.dart';
import 'package:vitalis/services/api_client.dart';
import 'package:vitalis/services/auth_service.dart';

class _FakeAuth implements AuthService {
  bool signInCalled = false;
  String? token;
  @override
  Future<String?> signIn() async {
    signInCalled = true;
    return token;
  }

  @override
  Future<String?> restoreSession() async => null;
  @override
  Future<void> signOut() async {}
}

Widget _wrap(AuthProvider auth) => ChangeNotifierProvider<AuthProvider>.value(
      value: auth,
      child: const MaterialApp(
        locale: Locale('he'),
        home: LoginScreen(),
      ),
    );

void main() {
  testWidgets('renders app name and sign-in button', (tester) async {
    final api = ApiClient(baseUrl: 'http://t/api', apiKey: 'k');
    final auth = AuthProvider(api, _FakeAuth());
    await tester.pumpWidget(_wrap(auth));

    expect(find.text('Vitalis'), findsOneWidget);
    expect(find.byKey(const ValueKey('login-signin-button')), findsOneWidget);
  });

  testWidgets('tapping sign-in invokes AuthProvider.signIn', (tester) async {
    final fakeAuth = _FakeAuth()..token = null; // cancelled
    final api = ApiClient(baseUrl: 'http://t/api', apiKey: 'k');
    final auth = AuthProvider(api, fakeAuth);
    await tester.pumpWidget(_wrap(auth));

    await tester.tap(find.byKey(const ValueKey('login-signin-button')));
    await tester.pump();

    expect(fakeAuth.signInCalled, isTrue);
  });
}
