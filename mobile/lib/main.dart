import 'dart:async';

import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import 'providers/auth_provider.dart';
import 'providers/biometrics_provider.dart';
import 'providers/favorites_provider.dart';
import 'providers/goals_program_provider.dart';
import 'providers/goals_provider.dart';
import 'providers/meal_provider.dart';
import 'providers/medical_provider.dart';
import 'providers/plan_provider.dart';
import 'providers/profile_provider.dart';
import 'providers/recommendation_provider.dart';
import 'providers/sleep_provider.dart';
import 'providers/summary_provider.dart';
import 'providers/templates_provider.dart';
import 'providers/training_provider.dart';
import 'router_guard.dart';
import 'screens/dashboard_screen.dart';
import 'screens/goals_screen.dart';
import 'screens/health_screen.dart';
import 'screens/history_screen.dart';
import 'screens/log_meal_screen.dart';
import 'screens/login_screen.dart';
import 'screens/meal_plan_screen.dart';
import 'screens/medical_screen.dart';
import 'screens/onboarding_screen.dart';
import 'screens/profile_screen.dart';
import 'screens/settings_screen.dart';
import 'screens/sleep_screen.dart';
import 'screens/splash_screen.dart';
import 'screens/training_screen.dart';
import 'screens/weekly_review_screen.dart';
import 'services/api_client.dart';
import 'services/app_auth_service.dart';
import 'services/document_picker.dart';
import 'services/health_connect.dart';
import 'services/image_service.dart';
import 'services/notification_handler.dart';
import 'services/push_service.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Firebase powers push notifications; it's optional, so never block app
  // start on a failure (e.g. missing google-services.json in a dev build).
  try {
    await Firebase.initializeApp();
  } catch (e) {
    debugPrint('Firebase init failed (notifications disabled): $e');
  }

  // Show a readable error screen instead of a blank/closed app when a
  // widget fails to build (visible even in release builds).
  ErrorWidget.builder = (FlutterErrorDetails details) => Directionality(
        textDirection: TextDirection.ltr,
        child: Material(
          color: const Color(0xFF7F0000),
          child: SafeArea(
            child: Padding(
              padding: const EdgeInsets.all(20),
              child: SingleChildScrollView(
                child: Text(
                  'Vitalis crashed on start:\n\n'
                  '${details.exceptionAsString()}\n\n'
                  '${details.stack}',
                  style: const TextStyle(color: Colors.white, fontSize: 12),
                ),
              ),
            ),
          ),
        ),
      );

  // TODO: Load from flutter_secure_storage
  const apiUrl = String.fromEnvironment(
    'API_URL',
    defaultValue: 'https://func-vitalis-api.azurewebsites.net/api',
  );
  // Transitional x-api-key fallback. Left empty in source so no key ships in
  // the public repo; real requests authenticate via SSO (bearer token). A key
  // can be injected at build time with --dart-define=API_KEY=... if needed.
  const apiKey = String.fromEnvironment('API_KEY', defaultValue: '');

  final apiClient = ApiClient(baseUrl: apiUrl, apiKey: apiKey);
  final healthConnect = HealthConnectService();
  final imageService = ImageService();
  final pushService = PushService(FirebasePushMessaging(), apiClient);

  runApp(
    MultiProvider(
      providers: [
        Provider<ApiClient>.value(value: apiClient),
        Provider<ImageService>.value(value: imageService),
        Provider<DocumentPicker>(create: (_) => DeviceDocumentPicker()),
        Provider<HealthConnectService>.value(value: healthConnect),
        Provider<PushService>.value(value: pushService),
        ChangeNotifierProvider(
          create: (_) => AuthProvider(apiClient, AppAuthService()),
        ),
        ChangeNotifierProvider(create: (_) => MealProvider(apiClient)),
        ChangeNotifierProvider(create: (_) => FavoritesProvider(apiClient)),
        ChangeNotifierProvider(create: (_) => TemplatesProvider(apiClient)),
        ChangeNotifierProvider(create: (_) => PlanProvider(apiClient)),
        ChangeNotifierProvider(create: (_) => GoalsProvider(apiClient)),
        ChangeNotifierProvider(create: (_) => SummaryProvider(apiClient)),
        ChangeNotifierProvider(create: (_) => RecommendationProvider(apiClient)),
        ChangeNotifierProvider(create: (_) => SleepProvider(apiClient)),
        ChangeNotifierProvider(create: (_) => TrainingProvider(apiClient)),
        ChangeNotifierProvider(create: (_) => GoalsProgramProvider(apiClient)),
        ChangeNotifierProvider(create: (_) => MedicalProvider(apiClient)),
        ChangeNotifierProvider(create: (_) => ProfileProvider(apiClient)),
        ChangeNotifierProxyProvider<AuthProvider, BiometricsProvider>(
          create: (_) => BiometricsProvider(
            healthConnect,
            apiClient: apiClient,
          ),
          update: (_, auth, biometrics) {
            final provider = biometrics!;
            unawaited(provider.setAuthenticatedUser(auth.userId));
            return provider;
          },
        ),
      ],
      child: const VitalisApp(),
    ),
  );
}

GoRouter _buildRouter(AuthProvider auth) => GoRouter(
      initialLocation: '/dashboard',
      refreshListenable: auth,
      redirect: (context, state) => authRedirect(
        isAuthenticated: auth.isAuthenticated,
        onboarded: auth.onboarded,
        location: state.matchedLocation,
        initializing: auth.initializing,
      ),
      routes: [
        GoRoute(
          path: '/splash',
          builder: (_, __) => const SplashScreen(),
        ),
        GoRoute(
          path: '/login',
          builder: (_, __) => const LoginScreen(),
        ),
        GoRoute(
          path: '/onboarding',
          builder: (_, __) => const OnboardingScreen(),
        ),
        StatefulShellRoute.indexedStack(
          builder: (context, state, child) => _AppShell(child: child),
          branches: [
            StatefulShellBranch(routes: [
              GoRoute(
                path: '/log',
                builder: (_, __) => const LogMealScreen(),
              ),
            ]),
            StatefulShellBranch(routes: [
          GoRoute(
            path: '/dashboard',
            builder: (_, __) => const DashboardScreen(),
          ),
        ]),
        StatefulShellBranch(routes: [
          GoRoute(
            path: '/health',
            builder: (_, __) => const HealthScreen(),
          ),
        ]),
        StatefulShellBranch(routes: [
          GoRoute(
            path: '/history',
            builder: (_, __) => const HistoryScreen(),
          ),
        ]),
        StatefulShellBranch(routes: [
          GoRoute(
            path: '/review',
            builder: (_, __) => const WeeklyReviewScreen(),
          ),
        ]),
      ],
    ),
    GoRoute(
      path: '/settings',
      builder: (_, __) => const SettingsScreen(),
    ),
    GoRoute(
      path: '/plan',
      builder: (_, __) => const MealPlanScreen(),
    ),
    GoRoute(
      path: '/sleep',
      builder: (_, __) => const SleepScreen(),
    ),
    GoRoute(
      path: '/training',
      builder: (_, __) => const TrainingScreen(),
    ),
    GoRoute(
      path: '/goals',
      builder: (_, __) => const GoalsScreen(),
    ),
    GoRoute(
      path: '/medical',
      builder: (_, __) => const MedicalScreen(),
    ),
    GoRoute(
      path: '/profile',
      builder: (_, __) => const ProfileScreen(),
    ),
  ],
);

class VitalisApp extends StatefulWidget {
  const VitalisApp({super.key});

  @override
  State<VitalisApp> createState() => _VitalisAppState();
}

class _VitalisAppState extends State<VitalisApp> with WidgetsBindingObserver {
  GoRouter? _router;
  NotificationHandler? _notifications;
  bool _pushRegistered = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addObserver(this);
    // Try to silently restore a previous SSO session on startup, and wire
    // notification foreground-display + tap-to-open once the router exists.
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted) return;
      context.read<AuthProvider>().tryRestore();
      _notifications = NotificationHandler((route) => _router?.go(route));
      _notifications!.init();
    });
    // Register this device for push once the user is authenticated.
    context.read<AuthProvider>().addListener(_maybeRegisterPush);
  }

  @override
  void dispose() {
    WidgetsBinding.instance.removeObserver(this);
    context.read<AuthProvider>().removeListener(_maybeRegisterPush);
    super.dispose();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    // Coming back to the foreground: proactively refresh the token so the first
    // request after a long background isn't a slow 401-then-refresh round trip.
    if (state == AppLifecycleState.resumed && mounted) {
      final auth = context.read<AuthProvider>();
      if (auth.isAuthenticated) {
        auth.refreshToken();
      }
    }
  }

  void _maybeRegisterPush() {
    if (_pushRegistered) return;
    if (context.read<AuthProvider>().isAuthenticated) {
      _pushRegistered = true;
      context.read<PushService>().register().catchError((_) {});
    }
  }

  @override
  Widget build(BuildContext context) {
    // Build the router once, bound to the shared AuthProvider for redirects.
    _router ??= _buildRouter(context.read<AuthProvider>());
    return MaterialApp.router(
      title: 'Vitalis',
      routerConfig: _router,
      locale: const Locale('he'),
      supportedLocales: const [Locale('he'), Locale('en')],
      localizationsDelegates: const [
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      theme: ThemeData(
        useMaterial3: true,
        colorSchemeSeed: Colors.green,
        brightness: Brightness.light,
      ),
      darkTheme: ThemeData(
        useMaterial3: true,
        colorSchemeSeed: Colors.green,
        brightness: Brightness.dark,
      ),
    );
  }
}

class _AppShell extends StatelessWidget {
  final Widget child;
  const _AppShell({required this.child});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: child,
      bottomNavigationBar: NavigationBar(
        selectedIndex: _currentIndex(context),
        onDestinationSelected: (i) => _onTap(context, i),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.add_circle), label: 'רישום'),
          NavigationDestination(icon: Icon(Icons.dashboard), label: 'לוח'),
          NavigationDestination(icon: Icon(Icons.favorite), label: 'בריאות'),
          NavigationDestination(icon: Icon(Icons.history), label: 'היסטוריה'),
          NavigationDestination(icon: Icon(Icons.insights), label: 'סקירה'),
        ],
      ),
    );
  }

  int _currentIndex(BuildContext context) {
    final location = GoRouterState.of(context).uri.path;
    if (location.startsWith('/log')) return 0;
    if (location.startsWith('/dashboard')) return 1;
    if (location.startsWith('/health')) return 2;
    if (location.startsWith('/history')) return 3;
    if (location.startsWith('/review')) return 4;
    return 1;
  }

  void _onTap(BuildContext context, int index) {
    switch (index) {
      case 0:
        context.go('/log');
      case 1:
        context.go('/dashboard');
      case 2:
        context.go('/health');
      case 3:
        context.go('/history');
      case 4:
        context.go('/review');
    }
  }
}
