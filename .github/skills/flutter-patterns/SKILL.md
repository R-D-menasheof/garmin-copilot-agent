---
name: flutter-patterns
description: "Flutter development patterns for Vitalis mobile app. Provider state management, Isar local DB, screen organization, image capture, RTL Hebrew support, GoRouter navigation, widget testing. Use when: Flutter code, mobile UI, Dart patterns, Provider, Isar, widget tests."
---

# Skill: Flutter Patterns

## Project Structure

```
mobile/
├── lib/
│   ├── main.dart                    # App entry, MultiProvider, GoRouter, Isar init
│   ├── models/                      # Dart data classes (mirror Pydantic models)
│   │   ├── meal_entry.dart
│   │   ├── nutrition_goal.dart
│   │   ├── daily_nutrition_log.dart
│   │   ├── biometrics_record.dart
│   │   └── known_food.dart
│   ├── providers/                   # ChangeNotifier state management
│   │   ├── meal_provider.dart       # Meal logging + daily totals
│   │   ├── goals_provider.dart      # Current goals + compliance
│   │   ├── biometrics_provider.dart # Latest biometrics
│   │   └── sync_provider.dart       # Offline queue + sync status
│   ├── screens/                     # Full-page widgets
│   │   ├── log_meal_screen.dart     # Text input, camera, history, direct entry
│   │   ├── dashboard_screen.dart    # Progress bars, macros, goal compliance
│   │   ├── history_screen.dart      # Daily meal logs, calendar view
│   │   └── settings_screen.dart     # API key, units, sync status
│   ├── services/                    # External integrations
│   │   ├── api_client.dart          # HTTP calls to Azure Functions
│   │   ├── health_connect.dart      # Health Connect read/write
│   │   ├── local_db.dart            # Isar operations
│   │   └── image_service.dart       # Camera + image picker
│   └── widgets/                     # Reusable components
│       ├── macro_bar.dart           # Colored progress bar for a macro
│       ├── meal_card.dart           # Single meal entry display
│       └── nutrient_ring.dart       # Circular progress for calories
├── test/
│   ├── providers/                   # Unit tests for providers
│   ├── services/                    # Unit tests for services (mocked)
│   └── screens/                     # Widget tests
├── pubspec.yaml
└── analysis_options.yaml
```

## Provider Pattern

### Rules
- **No business logic in widgets** — all state and logic lives in `ChangeNotifier` classes
- Widgets call `context.read<Provider>().method()` for actions
- Widgets use `context.watch<Provider>().field` for reactive UI
- One provider per domain concern (meals, goals, biometrics, sync)

### Setup in main.dart

```dart
void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final isar = await LocalDb.init();
  final apiClient = ApiClient();

  runApp(
    MultiProvider(
      providers: [
        ChangeNotifierProvider(create: (_) => MealProvider(isar, apiClient)),
        ChangeNotifierProvider(create: (_) => GoalsProvider(isar, apiClient)),
        ChangeNotifierProvider(create: (_) => BiometricsProvider(isar, apiClient)),
        ChangeNotifierProvider(create: (_) => SyncProvider(isar, apiClient)),
      ],
      child: const VitalisApp(),
    ),
  );
}
```

### Provider Template

```dart
class MealProvider extends ChangeNotifier {
  final Isar _isar;
  final ApiClient _api;

  List<MealEntry> _todayMeals = [];
  List<MealEntry> get todayMeals => _todayMeals;

  MealProvider(this._isar, this._api);

  Future<void> loadToday() async {
    _todayMeals = await _isar.mealEntrys
        .filter()
        .dateEqualTo(DateTime.now().toDateOnly())
        .findAll();
    notifyListeners();
  }

  Future<void> addMeal(MealEntry meal) async {
    await _isar.writeTxn(() => _isar.mealEntrys.put(meal));
    _todayMeals.add(meal);
    notifyListeners();
    // Queue for cloud sync
    await _api.postMeal(meal).catchError((_) {
      // Mark as unsynced for retry
    });
  }
}
```

## Isar Local Database

### Setup
- Register schemas in `main.dart`
- One Isar collection per data type: `MealEntry`, `NutritionGoal`, `BiometricsRecord`
- Add `synced` bool field for offline queue

### Schema Example

```dart
@collection
class MealEntry {
  Id id = Isar.autoIncrement;

  late String foodName;
  late int calories;
  late double proteinG;
  late double carbsG;
  late double fatG;
  double? fiberG;
  String? portionDescription;

  @Enumerated(EnumType.name)
  late NutritionSource source;

  late DateTime timestamp;
  late bool synced;  // false = queued for cloud sync
}
```

## Navigation (GoRouter)

```dart
final router = GoRouter(
  initialLocation: '/dashboard',
  routes: [
    StatefulShellRoute.indexedStack(
      builder: (context, state, child) => AppShell(child: child),
      branches: [
        StatefulShellBranch(routes: [
          GoRoute(path: '/log', builder: (_, __) => const LogMealScreen()),
        ]),
        StatefulShellBranch(routes: [
          GoRoute(path: '/dashboard', builder: (_, __) => const DashboardScreen()),
        ]),
        StatefulShellBranch(routes: [
          GoRoute(path: '/history', builder: (_, __) => const HistoryScreen()),
        ]),
        StatefulShellBranch(routes: [
          GoRoute(path: '/settings', builder: (_, __) => const SettingsScreen()),
        ]),
      ],
    ),
  ],
);
```

## RTL Hebrew Support

```dart
MaterialApp.router(
  routerConfig: router,
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
  ),
);
```

- All user-facing strings in Hebrew
- Technical terms (VO2max, HRV, BMI) stay in English
- Comments in English

## Image Capture

```dart
class ImageService {
  final ImagePicker _picker = ImagePicker();

  Future<Uint8List?> captureFromCamera() async {
    final file = await _picker.pickImage(source: ImageSource.camera, maxWidth: 1024);
    return file?.readAsBytes();
  }

  Future<Uint8List?> pickFromGallery() async {
    final file = await _picker.pickImage(source: ImageSource.gallery, maxWidth: 1024);
    return file?.readAsBytes();
  }
}
```

Image bytes are sent to `POST /api/v1/analyze-image` → Azure OpenAI vision → returns `list[MealEntry]`.

## Testing Conventions

### Service Tests (unit)
```dart
test('api_client sends correct body for postMeal', () async {
  final mockClient = MockHttpClient();
  final api = ApiClient(httpClient: mockClient);
  // ...assert request body matches expected
});
```

### Provider Tests (unit)
```dart
test('MealProvider.addMeal notifies listeners', () {
  final provider = MealProvider(mockIsar, mockApi);
  var notified = false;
  provider.addListener(() => notified = true);
  provider.addMeal(testMeal);
  expect(notified, isTrue);
});
```

### Widget Tests
```dart
testWidgets('LogMealScreen renders text input', (tester) async {
  await tester.pumpWidget(
    MultiProvider(
      providers: [ChangeNotifierProvider.value(value: mockMealProvider)],
      child: const MaterialApp(home: LogMealScreen()),
    ),
  );
  expect(find.byType(TextField), findsOneWidget);
});
```

## Key Packages

```yaml
dependencies:
  flutter:
    sdk: flutter
  provider: ^6.0.0
  isar: ^3.1.0
  isar_flutter_libs: ^3.1.0
  go_router: ^14.0.0
  image_picker: ^1.0.0
  health: ^10.0.0
  http: ^1.2.0
  flutter_secure_storage: ^9.0.0
  flutter_localizations:
    sdk: flutter
  intl: ^0.19.0

dev_dependencies:
  flutter_test:
    sdk: flutter
  mockito: ^5.4.0
  build_runner: ^2.4.0
  isar_generator: ^3.1.0
```
