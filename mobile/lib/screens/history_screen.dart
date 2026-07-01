import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/goals_provider.dart';
import '../providers/meal_provider.dart';
import '../widgets/calendar_week_row.dart';
import '../widgets/meal_card.dart';

/// History screen — daily meal logs with date navigation.
class HistoryScreen extends StatefulWidget {
  const HistoryScreen({super.key});

  @override
  State<HistoryScreen> createState() => _HistoryScreenState();
}

class _HistoryScreenState extends State<HistoryScreen> {
  DateTime _selectedDate = DateTime.now();
  late DateTime _weekStart = _weekStartFor(_selectedDate);

  static DateTime _weekStartFor(DateTime day) {
    // DateTime.weekday: Monday=1 ... Sunday=7. Days since the most recent
    // Sunday (0 when [day] itself is a Sunday).
    final daysSinceSunday = day.weekday % 7;
    return DateTime(day.year, day.month, day.day).subtract(Duration(days: daysSinceSunday));
  }

  @override
  void initState() {
    super.initState();
    Future.microtask(() {
      _loadDay();
      _loadWeek();
      context.read<MealProvider>().loadDayOverrides();
    });
  }

  Future<void> _loadDay() async {
    await context.read<MealProvider>().loadDay(_selectedDate);
  }

  Future<void> _loadWeek() async {
    await context.read<MealProvider>().loadRange(_weekStart, _weekStart.add(const Duration(days: 6)));
  }

  bool _isToday(DateTime d) {
    final now = DateTime.now();
    return d.year == now.year && d.month == now.month && d.day == now.day;
  }

  void _setSelectedDate(DateTime date) {
    setState(() {
      _selectedDate = date;
      _weekStart = _weekStartFor(date);
    });
    _loadDay();
    _loadWeek();
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
      _setSelectedDate(picked);
    }
  }

  void _prevDay() {
    _setSelectedDate(_selectedDate.subtract(const Duration(days: 1)));
  }

  void _nextDay() {
    if (!_isToday(_selectedDate)) {
      _setSelectedDate(_selectedDate.add(const Duration(days: 1)));
    }
  }

  void _prevWeek() {
    setState(() => _weekStart = _weekStart.subtract(const Duration(days: 7)));
    _loadWeek();
  }

  void _nextWeek() {
    setState(() => _weekStart = _weekStart.add(const Duration(days: 7)));
    _loadWeek();
  }

  String get _dateLabel {
    if (_isToday(_selectedDate)) return 'היום';
    final d = _selectedDate;
    return '${d.day}/${d.month}/${d.year}';
  }

  @override
  Widget build(BuildContext context) {
    final provider = context.watch<MealProvider>();
    final goal = context.watch<GoalsProvider>().currentGoal;
    final meals = provider.mealsForDay(_selectedDate);
    final loading = provider.isLoadingDay(_selectedDate);
    final error = provider.errorForDay(_selectedDate);
    final totalCalories = provider.totalCaloriesForDay(_selectedDate);
    final totalProtein = provider.totalProteinForDay(_selectedDate);
    final totalCarbs = provider.totalCarbsForDay(_selectedDate);
    final totalFat = provider.totalFatForDay(_selectedDate);
    final hasOverride = provider.hasManualOverride(_selectedDate);
    final weekStatuses = List.generate(
      7,
      (i) => provider.statusForDay(_weekStart.add(Duration(days: i)), goal),
    );

    return Scaffold(
      appBar: AppBar(title: const Text('היסטוריה')),
      body: Column(
        children: [
          // Calendar week row — navigation and pattern recognition
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            child: CalendarWeekRow(
              weekStart: _weekStart,
              selectedDay: _selectedDate,
              statuses: weekStatuses,
              onDaySelected: _setSelectedDate,
              onPrevWeek: _prevWeek,
              onNextWeek: _nextWeek,
            ),
          ),

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

          // Day tracking override toggle
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Align(
              alignment: Alignment.centerRight,
              child: TextButton.icon(
                onPressed: () => provider.toggleDayOverride(_selectedDate),
                icon: const Icon(Icons.label_outline, size: 18),
                label: Text(
                  hasOverride ? 'בטל סימון' : 'התיעוד לא משקף את היום הזה',
                ),
              ),
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
