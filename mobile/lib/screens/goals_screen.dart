import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/goals_program_provider.dart';

/// Goal programs screen — active programs with progress bars.
class GoalsScreen extends StatefulWidget {
  const GoalsScreen({super.key});

  @override
  State<GoalsScreen> createState() => _GoalsScreenState();
}

class _GoalsScreenState extends State<GoalsScreen> {
  @override
  void initState() {
    super.initState();
    Future.microtask(() => context.read<GoalsProgramProvider>().loadPrograms());
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<GoalsProgramProvider>();
    final programs = provider.programs;

    return Scaffold(
      appBar: AppBar(title: const Text('תוכניות יעדים')),
      body: provider.loading
          ? const Center(child: CircularProgressIndicator())
          : programs.isEmpty
              ? const Center(
                  child: Padding(
                    padding: EdgeInsets.all(32),
                    child: Text(
                      'אין תוכניות יעדים פעילות.\nבקש מ-Vitalis ליצור תוכנית.',
                      textAlign: TextAlign.center,
                    ),
                  ),
                )
              : ListView.separated(
                  padding: const EdgeInsets.all(16),
                  itemCount: programs.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 12),
                  itemBuilder: (context, index) {
                    final program = programs[index];
                    return Card(
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              children: [
                                Expanded(
                                  child: Text(
                                    program.nameHe,
                                    style: Theme.of(context).textTheme.titleMedium,
                                  ),
                                ),
                                if (program.active)
                                  const Chip(
                                    label: Text('פעיל'),
                                    backgroundColor: Colors.green,
                                    labelStyle: TextStyle(color: Colors.white, fontSize: 12),
                                  ),
                              ],
                            ),
                            if (program.descriptionHe.isNotEmpty) ...[
                              const SizedBox(height: 4),
                              Text(program.descriptionHe),
                            ],
                            const SizedBox(height: 12),
                            LinearProgressIndicator(
                              value: program.progressPct / 100,
                              minHeight: 8,
                              borderRadius: BorderRadius.circular(4),
                            ),
                            const SizedBox(height: 4),
                            Text('${program.progressPct.toStringAsFixed(0)}% התקדמות • ${program.durationWeeks} שבועות'),
                            if (program.milestones.isNotEmpty) ...[
                              const SizedBox(height: 12),
                              ...program.milestones.map((m) => ListTile(
                                    dense: true,
                                    leading: Icon(
                                      m.completed ? Icons.check_circle : Icons.radio_button_unchecked,
                                      color: m.completed ? Colors.green : Colors.grey,
                                    ),
                                    title: Text(m.titleHe),
                                    trailing: m.targetValue > 0
                                        ? Text('${m.currentValue.toStringAsFixed(1)} / ${m.targetValue.toStringAsFixed(1)}')
                                        : null,
                                  )),
                            ],
                          ],
                        ),
                      ),
                    );
                  },
                ),
    );
  }
}
