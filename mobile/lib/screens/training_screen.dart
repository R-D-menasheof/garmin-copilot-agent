import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/training_provider.dart';

/// Training program screen — weekly view with session cards.
class TrainingScreen extends StatefulWidget {
  const TrainingScreen({super.key});

  @override
  State<TrainingScreen> createState() => _TrainingScreenState();
}

class _TrainingScreenState extends State<TrainingScreen> {
  @override
  void initState() {
    super.initState();
    Future.microtask(() => context.read<TrainingProvider>().loadActiveProgram());
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<TrainingProvider>();
    final program = provider.activeProgram;

    return Scaffold(
      appBar: AppBar(title: const Text('תוכנית אימונים')),
      body: provider.loading
          ? const Center(child: CircularProgressIndicator())
          : program == null
              ? const Center(
                  child: Padding(
                    padding: EdgeInsets.all(32),
                    child: Text(
                      'אין תוכנית אימונים פעילה.\nבקש מ-Vitalis ליצור תוכנית עם /training-plan',
                      textAlign: TextAlign.center,
                    ),
                  ),
                )
              : ListView(
                  padding: const EdgeInsets.all(16),
                  children: [
                    // Program header
                    Card(
                      color: Theme.of(context).colorScheme.primaryContainer,
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              program.name,
                              style: Theme.of(context).textTheme.titleLarge,
                            ),
                            const SizedBox(height: 4),
                            Text('${program.durationWeeks} שבועות — ${program.goal}'),
                            const SizedBox(height: 8),
                            LinearProgressIndicator(
                              value: _completionPct(program),
                              minHeight: 8,
                              borderRadius: BorderRadius.circular(4),
                            ),
                            const SizedBox(height: 4),
                            Text('${(_completionPct(program) * 100).toStringAsFixed(0)}% הושלם'),
                          ],
                        ),
                      ),
                    ),
                    const SizedBox(height: 16),

                    // Weeks
                    for (int wi = 0; wi < program.weeks.length; wi++) ...[
                      Text(
                        'שבוע ${program.weeks[wi].weekNumber}',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: 8),
                      for (int si = 0; si < program.weeks[wi].sessions.length; si++)
                        _buildSessionCard(context, provider, wi, si, program.weeks[wi].sessions[si]),
                      const SizedBox(height: 16),
                    ],
                  ],
                ),
    );
  }

  Widget _buildSessionCard(
    BuildContext context,
    TrainingProvider provider,
    int weekIdx,
    int sessionIdx,
    dynamic session,
  ) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Card(
        color: session.completed ? Colors.green.withAlpha(20) : null,
        child: ListTile(
          leading: Icon(
            _typeIcon(session.type),
            color: session.completed ? Colors.green : null,
          ),
          title: Text(
            '${session.day} — ${session.type}',
            style: session.completed
                ? const TextStyle(decoration: TextDecoration.lineThrough)
                : null,
          ),
          subtitle: session.description.isNotEmpty
              ? Text('${session.description} • ${session.durationMin} דק\'')
              : Text('${session.durationMin} דק\''),
          trailing: Checkbox(
            value: session.completed,
            onChanged: (val) {
              provider.toggleSession(weekIdx, sessionIdx, val ?? false);
            },
          ),
        ),
      ),
    );
  }

  double _completionPct(dynamic program) {
    int total = 0;
    int done = 0;
    for (final week in program.weeks) {
      for (final session in week.sessions) {
        total++;
        if (session.completed) done++;
      }
    }
    return total > 0 ? done / total : 0;
  }

  IconData _typeIcon(String type) {
    switch (type) {
      case 'swimming':
        return Icons.pool;
      case 'strength':
        return Icons.fitness_center;
      case 'walk':
        return Icons.directions_walk;
      case 'rest':
        return Icons.self_improvement;
      case 'run':
        return Icons.directions_run;
      default:
        return Icons.sports;
    }
  }
}
