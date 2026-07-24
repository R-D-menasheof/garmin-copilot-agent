/// Entra External ID (CIAM) configuration for SSO.
///
/// Values from the `vitalisauth` external tenant. All are public
/// (client id + endpoints); no secrets live here.
class AuthConfig {
  static const String tenantId = '9b88e47d-4fb8-4538-8920-f4e3c8fbd9ac';

  /// Public client (mobile) application id.
  static const String clientId = '4077cdcc-4ac5-4f09-ad60-7add4276d8f3';

  /// OIDC authority (issuer base) for the external tenant.
  static const String authority =
      'https://vitalisauth.ciamlogin.com/$tenantId';

  static const String discoveryUrl =
      '$authority/v2.0/.well-known/openid-configuration';

  /// Android redirect URI — unique app-owned custom scheme. (Custom Tabs hand
  /// custom schemes back to the app reliably; https App Links have a Custom-Tab
  /// handoff quirk. The real blocker was MainActivity's taskAffinity="", which
  /// sent AppAuth's redirect to a different task — now removed.)
  static const String redirectUri = 'com.vitalis.vitalis://oauth2redirect';

  static const List<String> scopes = [
    'openid',
    'profile',
    'email',
    'offline_access',
  ];
}
