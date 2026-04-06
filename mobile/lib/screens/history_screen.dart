import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/meal_provider.dart';
import '../widgets/meal_card.dart';

/// History screen — daily meal logs with date navigation.
class HistoryScreen extends StatefulWidget {
  const HistoryScreen({super.key});

  @override
  State<HistoryScreen> createState() => _HistoryScreenState();
}

class _HistoryScreenState extends State<HistoryScreen> {
  DateTime _selectedDate = DateTime.now();

  @override
  void initState() {
    super.initState();
    Future.microtask(_loadDay);
  }

  Future<void> _loadDay() async {
    await context.read<MealProvider>().loadDay(_selectedDate);
  }

  bool _isToday(DateTime d) {
    final now = DateTime.now();
    return d.year == now.year && d.month == now.month && d.day == now.day;
  }

  Future<void> _pickDate() async {
    final picked = await showDatePicker(
      context: context,
      initialDate: _selectedDate,
      firstDate: DateTime(2026, 1, 1),
      lastDate: DateTime.now(),
      locale: const Locale('he'),
    );
    if (picked != null && picked != _selectedDate) {
      setState(() => _selectedDate = picked);
      _loadDay();
    }
  }

  void _prevDay() {
    setState(() => _selectedDate = _selectedDate.subtract(const Duration(days: 1)));
    _loadDay();
  }

  void _nextDay() {
    if (!_isToday(_selectedDate)) {
      setState(() => _selectedDate = _selectedDate.add(const Duration(days: 1)));
      Future.microtask(_loadDay);
    }
  }

  String get _dateLabel {
    if (_isToday(_selectedDate)) return 'היום';
    final d = _selectedDate;
    return '${d.day}/${d.month}/${d.year}';
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<MealProvider>();
    final meals = provider.mealsForDay(_selectedDate);
    final loading = provider.isLoadingDay(_selectedDate);
    final error = provider.errorForDay(_selectedDate);
    final totalCalories = provider.totalCaloriesForDay(_selectedDate);
    final totalProtein = provider.totalProteinForDay(_selectedDate);
    final totalCarbs = provider.totalCarbsForDay(_selectedDate);
    final totalFat = provider.totalFatForDay(_selectedDate);

    return Scaffold(
      appBar: AppBar(title: const Text('היסטוריה')),
      body: Column(
        children: [
          // Date navigation bar
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                IconButton(
                  icon: const Icon(Icons.chevron_right),
                  onPressed: _prevDay,
                ),
                TextButton(
                  onPressed: _pickDate,
                  child: Text(
                    _dateLabel,
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.chevron_left),
                  onPressed: _isToday(_selectedDate) ? null : _nextDay,
                ),
              ],
            ),
          ),

          // Day totals summary
          if (meals.isNotEmpty)
            Card(
              margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
              child: Padding(
                padding: const EdgeInsets.all(12),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceAround,
                  children: [
                    _TotalChip(label: 'קלוריות', value: '$totalCalories'),
                    _TotalChip(label: 'חלבון', value: '${totalProtein.toStringAsFixed(0)}g'),
                    _TotalChip(label: 'פחמימות', value: '${totalCarbs.toStringAsFixed(0)}g'),
                    _TotalChip(label: 'שומן', value: '${totalFat.toStringAsFixed(0)}g'),
                  ],
                ),
              ),
            ),

          // Meals list
          Expanded(
            child: loading
                ? const Center(child: CircularProgressIndicator())
                : error != null
                    ? Center(
                        child: Padding(
                          padding: const EdgeInsets.all(24),
                          child: Column(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Text(
                                'שגיאה בטעינת היסטוריה',
                                style: Theme.of(context).textTheme.titleMedium,
                              ),
                              const SizedBox(height: 8),
                              Text(error, textAlign: TextAlign.center),
                              const SizedBox(height: 12),
                              FilledButton(
                                onPressed: _loadDay,
                                child: const Text('נסה שוב'),
                              ),
                            ],
                          ),
                        ),
                      )
                    : meals.isEmpty
                    ? Center(
                        child: Text(
                          'אין ארוחות ליום זה',
                          style: Theme.of(context).textTheme.bodyLarge,
                        ),
                      )
                    : ListView.builder(
                        padding: const EdgeInsets.symmetric(horizontal: 16),
                        itemCount: meals.length,
                        itemBuilder: (_, i) => MealCard(
                          meal: meals[i],
                          index: i,
                          onDelete: (index) =>
                              provider.removeMeal(_selectedDate, index),
                          onEdit: (index, updated) =>
                              provider.updateMeal(_selectedDate, index, updated),
                        ),
                      ),
          ),
        ],
      ),
    );
  }
}

class _TotalChip extends StatelessWidget {
  final String label;
  final String value;

  const _TotalChip({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        Text(value, style: Theme.of(context).textTheme.titleSmall?.copyWith(fontWeight: FontWeight.bold)),
        Text(label, style: Theme.of(context).textTheme.bodySmall),
      ],
    );
  }
}
