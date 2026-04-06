import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import 'providers/biometrics_provider.dart';
import 'providers/favorites_provider.dart';
import 'providers/goals_provider.dart';
import 'providers/meal_provider.dart';
import 'providers/plan_provider.dart';
import 'providers/summary_provider.dart';
import 'providers/templates_provider.dart';
import 'screens/dashboard_screen.dart';
import 'screens/health_screen.dart';
import 'screens/history_screen.dart';
import 'screens/log_meal_screen.dart';
import 'screens/meal_plan_screen.dart';
import 'screens/settings_screen.dart';
import 'screens/weekly_review_screen.dart';
import 'services/api_client.dart';
import 'services/health_connect.dart';
import 'services/image_service.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();

  // TODO: Load from flutter_secure_storage
  const apiUrl = String.fromEnvironment(
    'API_URL',
    defaultValue: 'https://func-vitalis-api.azurewebsites.net/api',
  );
  const apiKey = String.fromEnvironment(
    'API_KEY',
    defaultValue: 'PdVicIlE5QN27FwSk6rOjbvZMLzhpC1s',
  );

  final apiClient = ApiClient(baseUrl: apiUrl, apiKey: apiKey);
  final healthConnect = HealthConnectService();
  final imageService = ImageService();

  runApp(
    MultiProvider(
      providers: [
        Provider<ApiClient>.value(value: apiClient),
        Provider<ImageService>.value(value: imageService),
        Provider<HealthConnectService>.value(value: healthConnect),
        ChangeNotifierProvider(create: (_) => MealProvider(apiClient)),
        ChangeNotifierProvider(create: (_) => FavoritesProvider(apiClient)),
        ChangeNotifierProvider(create: (_) => TemplatesProvider(apiClient)),
        ChangeNotifierProvider(create: (_) => PlanProvider(apiClient)),
        ChangeNotifierProvider(create: (_) => GoalsProvider(apiClient)),
        ChangeNotifierProvider(create: (_) => SummaryProvider(apiClient)),
        ChangeNotifierProvider(create: (_) {
          final provider = BiometricsProvider(
            healthConnect,
            apiClient: apiClient,
          );
          provider.init(); // Load Health Connect data on startup
          return provider;
        }),
      ],
      child: const VitalisApp(),
    ),
  );
}

final _router = GoRouter(
  initialLocation: '/dashboard',
  routes: [
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
            path: '/settings',
            builder: (_, __) => const SettingsScreen(),
          ),
        ]),
      ],
    ),
    GoRoute(
      path: '/review',
      builder: (_, __) => const WeeklyReviewScreen(),
    ),
    GoRoute(
      path: '/plan',
      builder: (_, __) => const MealPlanScreen(),
    ),
  ],
);

class VitalisApp extends StatelessWidget {
  const VitalisApp({super.key});

  @override
  Widget build(BuildContext context) {
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
          NavigationDestination(icon: Icon(Icons.settings), label: 'הגדרות'),
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
    if (location.startsWith('/settings')) return 4;
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
        context.go('/settings');
    }
  }
}
