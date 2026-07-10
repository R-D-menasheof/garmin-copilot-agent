import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/auth_provider.dart';

/// Sign-in screen (Entra External ID SSO). Shown when unauthenticated.
class LoginScreen extends StatelessWidget {
  const LoginScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();

    return Scaffold(
      body: SafeArea(
        child: Center(
          child: Padding(
            padding: const EdgeInsets.all(32),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.favorite, size: 72, color: Colors.green),
                const SizedBox(height: 16),
                Text(
                  'Vitalis',
                  style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                        fontWeight: FontWeight.bold,
                      ),
                ),
                const SizedBox(height: 8),
                const Text(
                  'המלווה האישי לבריאות וכושר',
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 40),
                if (auth.busy)
                  const CircularProgressIndicator()
                else
                  FilledButton.icon(
                    key: const ValueKey('login-signin-button'),
                    onPressed: () => _signIn(context, auth),
                    icon: const Icon(Icons.login),
                    label: const Text('התחברות / הרשמה'),
                    style: FilledButton.styleFrom(
                      minimumSize: const Size.fromHeight(52),
                    ),
                  ),
                const SizedBox(height: 12),
                const Text(
                  'התחברות מאובטחת דרך Microsoft Entra',
                  style: TextStyle(fontSize: 12, color: Colors.grey),
                  textAlign: TextAlign.center,
                ),
                if (auth.lastError != null) ...[
                  const SizedBox(height: 20),
                  Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: const Color(0xFFFDECEA),
                      border: Border.all(color: Colors.red),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: SelectableText(
                      'שגיאה (screenshot this):\n${auth.lastError}',
                      textDirection: TextDirection.ltr,
                      style: const TextStyle(
                          fontSize: 12, color: Color(0xFFB00020)),
                    ),
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }

  Future<void> _signIn(BuildContext context, AuthProvider auth) async {
    final ok = await auth.signIn();
    if (!ok && context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(auth.lastError ?? 'ההתחברות נכשלה. נסה שוב.'),
          duration: const Duration(seconds: 8),
        ),
      );
    }
  }
}
