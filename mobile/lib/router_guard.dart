/// Pure routing-guard logic for auth + onboarding, extracted for testability.
///
/// Returns the path to redirect to, or null to allow the current [location].
String? authRedirect({
  required bool isAuthenticated,
  required bool onboarded,
  required String location,
  bool initializing = false,
}) {
  const login = '/login';
  const onboarding = '/onboarding';
  const splash = '/splash';

  // While the session is being silently restored, hold on a splash screen so
  // the login screen doesn't flash before restore completes.
  if (initializing) {
    return location == splash ? null : splash;
  }

  if (!isAuthenticated) {
    return location == login ? null : login;
  }
  if (!onboarded) {
    return location == onboarding ? null : onboarding;
  }
  // Authenticated + onboarded: keep them out of the auth-only / splash screens.
  if (location == login || location == onboarding || location == splash) {
    return '/dashboard';
  }
  return null;
}
