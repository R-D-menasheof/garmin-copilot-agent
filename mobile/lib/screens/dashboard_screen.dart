import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../providers/goals_provider.dart';
import '../providers/meal_provider.dart';
import '../providers/summary_provider.dart';
import '../widgets/macro_bar.dart';

/// Dashboard screen — calories progress, macro breakdown, goal compliance.
class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  @override
  void initState() {
    super.initState();
    Future.microtask(() {
      context.read<MealProvider>().loadToday();
      context.read<GoalsProvider>().loadGoals();
      context.read<SummaryProvider>().loadLatestSummary();
    });
  }

  @override
  Widget build(BuildContext context) {
    final meals = context.watch<MealProvider>();
    final goals = context.watch<GoalsProvider>();
    final summary = context.watch<SummaryProvider>();
    final goal = goals.currentGoal;
    final latestSummary = summary.latestSummary;

    final caloriesTarget = goal?.caloriesTarget ?? 2200;
    final proteinTarget = goal?.proteinGTarget ?? 180;
    final carbsTarget = goal?.carbsGTarget ?? 250;
    final fatTarget = goal?.fatGTarget ?? 70;

    final compliancePct = goals.compliancePct(meals.totalCalories);

    return Scaffold(
      appBar: AppBar(title: const Text('Vitalis')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
            // Calories progress
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  children: [
                    Text(
                      '${meals.totalCalories}',
                      style: Theme.of(context).textTheme.headlineLarge,
                    ),
                    Text(
                      'מתוך $caloriesTarget קלוריות',
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                    if (goals.isAgentManagedGoal)
                      Text(
                        'יעד שהוגדר על ידי Vitalis',
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                    const SizedBox(height: 8),
                    LinearProgressIndicator(
                      value: caloriesTarget > 0
                          ? (meals.totalCalories / caloriesTarget).clamp(0.0, 1.0)
                          : 0,
                      minHeight: 12,
                      borderRadius: BorderRadius.circular(6),
                    ),
                    if (compliancePct != null) ...[
                      const SizedBox(height: 4),
                      Text('${compliancePct.toStringAsFixed(0)}% עמידה ביעד'),
                    ],
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Align(
                  alignment: Alignment.centerRight,
                  child: FilledButton.icon(
                    onPressed: () => context.push('/plan'),
                    icon: const Icon(Icons.event_note_outlined),
                    label: const Text('תכנון יום'),
                  ),
                ),
              ),
            ),
            if (latestSummary != null) ...[
              const SizedBox(height: 16),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Text(
                        'תובנה יומית',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: 8),
                      if (latestSummary.trends.isNotEmpty)
                        Text(latestSummary.trends.first),
                      if (latestSummary.recommendations.isNotEmpty) ...[
                        const SizedBox(height: 8),
                        Text(
                          latestSummary.recommendations.first.title,
                          style: Theme.of(context).textTheme.bodyLarge,
                        ),
                        const SizedBox(height: 8),
                        Align(
                          alignment: Alignment.centerRight,
                          child: TextButton.icon(
                            onPressed: () => context.push('/review'),
                            icon: const Icon(Icons.insights_outlined),
                            label: const Text('סקירה שבועית'),
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
              ),
            ],
            const SizedBox(height: 16),
            // Macro breakdown
            MacroBar(
              label: 'חלבון',
              current: meals.totalProtein,
              target: proteinTarget,
              color: Colors.blue,
            ),
            const SizedBox(height: 12),
            MacroBar(
              label: 'פחמימות',
              current: meals.totalCarbs,
              target: carbsTarget,
              color: Colors.orange,
            ),
            const SizedBox(height: 12),
            MacroBar(
              label: 'שומן',
              current: meals.totalFat,
              target: fatTarget,
              color: Colors.red,
            ),
        ],
      ),
    );
  }
}
