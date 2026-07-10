import 'package:flutter_test/flutter_test.dart';
import 'package:vitalis/router_guard.dart';

void main() {
  group('authRedirect', () {
    test('unauthenticated is sent to /login', () {
      expect(
        authRedirect(isAuthenticated: false, onboarded: false, location: '/dashboard'),
        '/login',
      );
    });

    test('unauthenticated already on /login stays', () {
      expect(
        authRedirect(isAuthenticated: false, onboarded: false, location: '/login'),
        isNull,
      );
    });

    test('authenticated but not onboarded goes to /onboarding', () {
      expect(
        authRedirect(isAuthenticated: true, onboarded: false, location: '/dashboard'),
        '/onboarding',
      );
    });

    test('authenticated not onboarded already on /onboarding stays', () {
      expect(
        authRedirect(isAuthenticated: true, onboarded: false, location: '/onboarding'),
        isNull,
      );
    });

    test('authenticated + onboarded on /login is sent to /dashboard', () {
      expect(
        authRedirect(isAuthenticated: true, onboarded: true, location: '/login'),
        '/dashboard',
      );
    });

    test('authenticated + onboarded on /onboarding is sent to /dashboard', () {
      expect(
        authRedirect(isAuthenticated: true, onboarded: true, location: '/onboarding'),
        '/dashboard',
      );
    });

    test('authenticated + onboarded on a normal route stays', () {
      expect(
        authRedirect(isAuthenticated: true, onboarded: true, location: '/history'),
        isNull,
      );
    });

    test('while initializing, any route redirects to /splash', () {
      expect(
        authRedirect(
          isAuthenticated: false,
          onboarded: false,
          location: '/dashboard',
          initializing: true,
        ),
        '/splash',
      );
    });

    test('while initializing, /splash stays', () {
      expect(
        authRedirect(
          isAuthenticated: false,
          onboarded: false,
          location: '/splash',
          initializing: true,
        ),
        isNull,
      );
    });

    test('after init, /splash for an authed+onboarded user goes to /dashboard', () {
      expect(
        authRedirect(
          isAuthenticated: true,
          onboarded: true,
          location: '/splash',
        ),
        '/dashboard',
      );
    });

    test('after init, /splash for an unauthenticated user goes to /login', () {
      expect(
        authRedirect(
          isAuthenticated: false,
          onboarded: false,
          location: '/splash',
        ),
        '/login',
      );
    });
  });
}
