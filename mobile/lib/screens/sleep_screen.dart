import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../models/sleep_models.dart';
import '../providers/sleep_provider.dart';

/// Sleep protocol screen — evening checklist + morning rating.
class SleepScreen extends StatefulWidget {
  const SleepScreen({super.key});

  @override
  State<SleepScreen> createState() => _SleepScreenState();
}

class _SleepScreenState extends State<SleepScreen> {
  @override
  void initState() {
    super.initState();
    Future.microtask(() => context.read<SleepProvider>().loadProtocol());
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<SleepProvider>();
    final checklist = provider.checklist;
    final todayEntry = provider.todayEntry;

    return Scaffold(
      appBar: AppBar(title: const Text('פרוטוקול שינה')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // Bedtime target
          Card(
            color: Colors.indigo.withAlpha(20),
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                children: [
                  const Icon(Icons.bedtime, size: 32, color: Colors.indigo),
                  const SizedBox(height: 8),
                  Text(
                    'יעד שינה: 23:00',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  if (_minutesToBedtime() > 0)
                    Text('עוד ${_minutesToBedtime()} דקות'),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),

          // Checklist
          Text('צ\'קליסט ערב', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          if (checklist != null)
            ...checklist.items.map((item) => CheckboxListTile(
                  value: item.checked,
                  title: Text(item.labelHe),
                  secondary: _categoryIcon(item.category),
                  onChanged: (val) {
                    provider.toggleChecklistItem(item.id, val ?? false);
                  },
                ))
          else
            const Center(child: Text('אין פרוטוקול שינה עדיין')),

          const SizedBox(height: 24),

          // Morning rating
          Text('דירוג בוקר', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                children: [
                  Text(
                    'איך ישנת?',
                    style: Theme.of(context).textTheme.bodyLarge,
                  ),
                  const SizedBox(height: 8),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: List.generate(5, (i) {
                      final rating = i + 1;
                      final selected = (todayEntry?.rating ?? 0) >= rating;
                      return IconButton(
                        icon: Icon(
                          selected ? Icons.star : Icons.star_border,
                          color: selected ? Colors.amber : Colors.grey,
                          size: 36,
                        ),
                        onPressed: () => provider.rateSleep(rating),
                      );
                    }),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  int _minutesToBedtime() {
    final now = TimeOfDay.now();
    const target = TimeOfDay(hour: 23, minute: 0);
    final diff = (target.hour * 60 + target.minute) - (now.hour * 60 + now.minute);
    return diff > 0 ? diff : 0;
  }

  Widget _categoryIcon(String category) {
    switch (category) {
      case 'wind_down':
        return const Icon(Icons.nights_stay, color: Colors.indigo);
      case 'environment':
        return const Icon(Icons.thermostat, color: Colors.blue);
      case 'habits':
        return const Icon(Icons.no_drinks, color: Colors.orange);
      default:
        return const Icon(Icons.check_circle_outline);
    }
  }
}
