import 'package:flutter/material.dart';

import '../providers/meal_provider.dart';

/// A week of 7 status dots (Sunday–Saturday) used in the History screen
/// for quick navigation and pattern recognition. Not used for balance
/// math — just visual orientation and jump-to-day.
class CalendarWeekRow extends StatelessWidget {
  /// The Sunday that starts the displayed week.
  final DateTime weekStart;
  final DateTime selectedDay;

  /// Status for each day of the week, Sunday first — must have length 7.
  final List<DayStatus> statuses;

  final ValueChanged<DateTime> onDaySelected;
  final VoidCallback? onPrevWeek;
  final VoidCallback? onNextWeek;

  static const _dayLabels = ['א', 'ב', 'ג', 'ד', 'ה', 'ו', 'ש'];

  const CalendarWeekRow({
    super.key,
    required this.weekStart,
    required this.selectedDay,
    required this.statuses,
    required this.onDaySelected,
    this.onPrevWeek,
    this.onNextWeek,
  });

  bool _isSameDay(DateTime a, DateTime b) =>
      a.year == b.year && a.month == b.month && a.day == b.day;

  Color _colorForStatus(DayStatus status) {
    switch (status) {
      case DayStatus.trackedWithinBudget:
        return Colors.green;
      case DayStatus.trackedExceeded:
        return Colors.red;
      case DayStatus.untracked:
        return Colors.grey.shade300;
      case DayStatus.future:
        return Colors.grey.shade100;
    }
  }

  @override
  Widget build(BuildContext context) {
    final weekEnd = weekStart.add(const Duration(days: 6));

    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            IconButton(
              icon: const Icon(Icons.keyboard_double_arrow_right),
              onPressed: onPrevWeek,
            ),
            Text(
              'השבוע: ${weekStart.day}/${weekStart.month} – ${weekEnd.day}/${weekEnd.month}',
              style: Theme.of(context).textTheme.bodyMedium,
            ),
            IconButton(
              icon: const Icon(Icons.keyboard_double_arrow_left),
              onPressed: onNextWeek,
            ),
          ],
        ),
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceEvenly,
          children: List.generate(7, (i) {
            final day = weekStart.add(Duration(days: i));
            final isSelected = _isSameDay(day, selectedDay);
            return GestureDetector(
              key: ValueKey('calendar-dot-$i'),
              onTap: () => onDaySelected(day),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(_dayLabels[i], style: Theme.of(context).textTheme.bodySmall),
                  const SizedBox(height: 4),
                  Container(
                    width: 24,
                    height: 24,
                    decoration: BoxDecoration(
                      color: _colorForStatus(statuses[i]),
                      shape: BoxShape.circle,
                      border: isSelected
                          ? Border.all(
                              color: Theme.of(context).colorScheme.primary,
                              width: 2,
                            )
                          : null,
                    ),
                  ),
                ],
              ),
            );
          }),
        ),
      ],
    );
  }
}
