import 'package:fl_chart/fl_chart.dart';
import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

/// Reusable line chart widget for health metric trends.
class TrendChart extends StatefulWidget {
  final String title;
  final String unit;
  final Color color;
  final List<(DateTime, double)> data;
  final String axisDateFormat;

  const TrendChart({
    super.key,
    required this.title,
    required this.unit,
    required this.color,
    required this.data,
    this.axisDateFormat = 'd/M',
  });

  static String formatFullDate(DateTime date) => DateFormat('dd/MM/yyyy').format(date);

  @override
  State<TrendChart> createState() => _TrendChartState();
}

class _TrendChartState extends State<TrendChart> {
  int _selectedIndex = 0;

  @override
  void initState() {
    super.initState();
    _selectedIndex = widget.data.isEmpty ? 0 : widget.data.length - 1;
  }

  @override
  void didUpdateWidget(covariant TrendChart oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.data.isEmpty) {
      _selectedIndex = 0;
      return;
    }
    if (oldWidget.data.length != widget.data.length || _selectedIndex >= widget.data.length) {
      _selectedIndex = widget.data.length - 1;
    }
  }

  @override
  Widget build(BuildContext context) {
    if (widget.data.isEmpty) {
      return Card(
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            children: [
              Text(widget.title, style: Theme.of(context).textTheme.titleSmall),
              const SizedBox(height: 16),
              const Text('אין נתונים'),
            ],
          ),
        ),
      );
    }

    final selectedDate = widget.data[_selectedIndex].$1;
    final spots = widget.data
        .asMap()
        .entries
        .map((e) => FlSpot(e.key.toDouble(), e.value.$2))
        .toList();

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '${widget.title} (${widget.unit})',
              style: Theme.of(context).textTheme.titleSmall,
            ),
            const SizedBox(height: 12),
            SizedBox(
              height: 150,
              child: LineChart(
                LineChartData(
                  gridData: const FlGridData(show: true, drawVerticalLine: false),
                  lineTouchData: LineTouchData(
                    enabled: true,
                    handleBuiltInTouches: true,
                    touchCallback: (event, response) {
                      final spot = response?.lineBarSpots?.firstOrNull;
                      if (spot == null) {
                        return;
                      }
                      final index = spot.x.toInt();
                      if (index == _selectedIndex || index < 0 || index >= widget.data.length) {
                        return;
                      }
                      setState(() {
                        _selectedIndex = index;
                      });
                    },
                    touchTooltipData: LineTouchTooltipData(
                      getTooltipItems: (touchedSpots) {
                        return touchedSpots.map((spot) {
                          final index = spot.x.toInt();
                          final date = widget.data[index].$1;
                          return LineTooltipItem(
                            '${TrendChart.formatFullDate(date)}\n${spot.y.toStringAsFixed(1)} ${widget.unit}',
                            Theme.of(context).textTheme.bodySmall ?? const TextStyle(fontSize: 12),
                          );
                        }).toList();
                      },
                    ),
                  ),
                  titlesData: FlTitlesData(
                    topTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                    rightTitles: const AxisTitles(sideTitles: SideTitles(showTitles: false)),
                    bottomTitles: AxisTitles(
                      sideTitles: SideTitles(
                        showTitles: true,
                        reservedSize: 32,
                        interval: 1,
                        getTitlesWidget: (value, meta) {
                          final idx = value.toInt();
                          if (idx < 0 || idx >= widget.data.length) {
                            return const SizedBox.shrink();
                          }
                          return Padding(
                            padding: const EdgeInsets.only(top: 4),
                            child: Text(
                              DateFormat(widget.axisDateFormat).format(widget.data[idx].$1),
                              style: const TextStyle(fontSize: 10),
                            ),
                          );
                        },
                      ),
                    ),
                    leftTitles: AxisTitles(
                      sideTitles: SideTitles(
                        showTitles: true,
                        reservedSize: 40,
                        getTitlesWidget: (value, meta) {
                          return Text(
                            value.toStringAsFixed(0),
                            style: const TextStyle(fontSize: 10),
                          );
                        },
                      ),
                    ),
                  ),
                  borderData: FlBorderData(show: false),
                  lineBarsData: [
                    LineChartBarData(
                      spots: spots,
                      showingIndicators: [_selectedIndex],
                      isCurved: true,
                      color: widget.color,
                      barWidth: 2.5,
                      dotData: const FlDotData(show: true),
                      belowBarData: BarAreaData(
                        show: true,
                        color: widget.color.withAlpha(30),
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 8),
            Text(
              'בדיקה נבחרת: ${TrendChart.formatFullDate(selectedDate)}',
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ],
        ),
      ),
    );
  }
}
