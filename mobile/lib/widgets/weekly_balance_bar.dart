import 'package:flutter/material.dart';

/// Rolling 7-day calorie balance indicator, shown on the dashboard below
/// the daily calories card. Excludes untracked days from the sum (see
/// `MealProvider.rollingWeekBalance`).
class WeeklyBalanceBar extends StatelessWidget {
  /// Sum of (actual - target) calories over the window, or null when no
  /// goal is set (in which case this widget renders nothing).
  final int? balance;

  /// How many of [totalDays] are tracked (counted in [balance]).
  final int trackedDays;

  final int totalDays;

  /// Cumulative surplus (kcal) above which the bar switches to warning
  /// styling instead of the default green/neutral styling.
  static const int _significantSurplusThreshold = 500;

  const WeeklyBalanceBar({
    super.key,
    required this.balance,
    required this.trackedDays,
    this.totalDays = 7,
  });

  @override
  Widget build(BuildContext context) {
    final balance = this.balance;
    if (balance == null) {
      return const SizedBox.shrink();
    }

    final isSignificantSurplus = balance > _significantSurplusThreshold;
    final color = isSignificantSurplus ? Colors.orange : Colors.green;
    final sign = balance > 0 ? '+' : '';

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'מאזן $totalDays ימים אחרונים: $sign$balance קק"ל',
              style: Theme.of(context)
                  .textTheme
                  .bodyMedium
                  ?.copyWith(color: color, fontWeight: FontWeight.bold),
            ),
            const SizedBox(height: 8),
            LinearProgressIndicator(
              value: totalDays > 0 ? (trackedDays / totalDays).clamp(0.0, 1.0) : 0,
              color: color,
              backgroundColor: color.withOpacity(0.2),
              minHeight: 8,
              borderRadius: BorderRadius.circular(4),
            ),
            const SizedBox(height: 4),
            Text(
              '$trackedDays/$totalDays ימים תועדו',
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ],
        ),
      ),
    );
  }
}
