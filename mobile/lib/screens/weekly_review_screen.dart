import 'package:flutter/material.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:provider/provider.dart';

import '../models/health_data_models.dart';
import '../models/recommendation_status.dart';
import '../models/timeline_event.dart';
import '../providers/recommendation_provider.dart';
import '../providers/summary_provider.dart';
import '../services/api_client.dart';
import '../widgets/trend_chart.dart';

class WeeklyReviewScreen extends StatefulWidget {
  const WeeklyReviewScreen({super.key});

  @override
  State<WeeklyReviewScreen> createState() => _WeeklyReviewScreenState();
}

class _WeeklyReviewScreenState extends State<WeeklyReviewScreen> {
  @override
  void initState() {
    super.initState();
    Future.microtask(() {
      final provider = context.read<SummaryProvider>();
      if (provider.latestSummary == null) {
        provider.loadLatestSummary();
      }
      if (provider.summaryHistory.isEmpty) {
        provider.loadSummaryHistory(limit: 6);
      }
      context.read<RecommendationProvider>().loadStatuses();
    });
  }

  @override
  Widget build(BuildContext context) {
    final summaryProvider = context.watch<SummaryProvider>();
    final latest = summaryProvider.latestSummary;

    return DefaultTabController(
      length: 5,
      child: Scaffold(
        appBar: AppBar(
          title: const Text('סקירה שבועית'),
          bottom: const TabBar(
            isScrollable: true,
            tabs: [
              Tab(text: 'משימות'),
              Tab(text: 'דוח'),
              Tab(text: 'מגמות'),
              Tab(text: 'ציר זמן'),
              Tab(text: 'מעבדה'),
            ],
          ),
        ),
        body: summaryProvider.loading && latest == null
            ? const Center(child: CircularProgressIndicator())
            : latest == null
                ? const Center(child: Text('אין עדיין סקירות זמינות'))
                : TabBarView(
                    children: [
                      _TodoTab(summary: latest),
                      _ReportTab(summary: latest),
                      const _TrendsTab(),
                      const _TimelineTab(),
                      const _LabTrendsTab(),
                    ],
                  ),
      ),
    );
  }
}

class _TodoTab extends StatelessWidget {
  final dynamic summary;
  const _TodoTab({required this.summary});

  @override
  Widget build(BuildContext context) {
    final allRecs = summary.recommendations as List;
    if (allRecs.isEmpty) {
      return const Center(child: Text('אין המלצות'));
    }

    final actionItems = allRecs.where((r) => r.priority < 5).toList();
    final achievements = allRecs.where((r) => r.priority == 5).toList();
    final recProvider = context.watch<RecommendationProvider>();

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        if (actionItems.isNotEmpty) ...[
          Text('משימות', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          for (final rec in actionItems)
            _buildActionItem(context, rec, recProvider),
        ],
        if (achievements.isNotEmpty) ...[
          const SizedBox(height: 20),
          Text('הישגים ✨', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          for (final rec in achievements)
            _buildAchievement(context, rec),
        ],
      ],
    );
  }

  Widget _buildActionItem(BuildContext context, dynamic rec, RecommendationProvider recProvider) {
    final recId = RecommendationStatus.generateId(rec.category, rec.title);
    final status = recProvider.getStatus(recId);
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Dismissible(
        key: Key(recId),
        background: Container(
          alignment: Alignment.centerLeft,
          padding: const EdgeInsets.only(left: 20),
          color: Colors.green.withAlpha(40),
          child: const Icon(Icons.check, color: Colors.green),
        ),
        secondaryBackground: Container(
          alignment: Alignment.centerRight,
          padding: const EdgeInsets.only(right: 20),
          color: Colors.orange.withAlpha(40),
          child: const Icon(Icons.snooze, color: Colors.orange),
        ),
        confirmDismiss: (direction) async {
          if (direction == DismissDirection.startToEnd) {
            await recProvider.markDone(recId);
          } else {
            await recProvider.markSnoozed(recId);
          }
          return false;
        },
        child: Card(
          color: status == RecStatus.done
              ? Colors.green.withAlpha(20)
              : status == RecStatus.snoozed
                  ? Colors.orange.withAlpha(20)
                  : null,
          child: ListTile(
            leading: Checkbox(
              value: status == RecStatus.done,
              onChanged: (val) {
                if (val == true) {
                  recProvider.markDone(recId);
                } else {
                  recProvider.markPending(recId);
                }
              },
            ),
            title: Text(
              rec.title,
              style: status == RecStatus.done
                  ? const TextStyle(decoration: TextDecoration.lineThrough)
                  : null,
            ),
            subtitle: Text(rec.detail),
            trailing: _priorityBadge(rec.priority),
          ),
        ),
      ),
    );
  }

  Widget _buildAchievement(BuildContext context, dynamic rec) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Card(
        color: Colors.green.withAlpha(15),
        child: ListTile(
          leading: const Text('🏆', style: TextStyle(fontSize: 24)),
          title: Text(rec.title),
          subtitle: Text(rec.detail),
        ),
      ),
    );
  }

  Widget _priorityBadge(int priority) {
    final color = priority <= 2
        ? Colors.red
        : priority <= 3
            ? Colors.orange
            : Colors.green;
    return CircleAvatar(
      radius: 14,
      backgroundColor: color.withAlpha(40),
      child: Text(
        'P$priority',
        style: TextStyle(fontSize: 11, color: color, fontWeight: FontWeight.bold),
      ),
    );
  }
}

class _ReportTab extends StatefulWidget {
  final dynamic summary;
  const _ReportTab({required this.summary});

  @override
  State<_ReportTab> createState() => _ReportTabState();
}

class _ReportTabState extends State<_ReportTab> {
  int _selectedIndex = 0;

  @override
  Widget build(BuildContext context) {
    final summaryProvider = context.watch<SummaryProvider>();
    final history = summaryProvider.summaryHistory;
    final current = _selectedIndex < history.length
        ? history[_selectedIndex]
        : widget.summary;
    final md = (current.reportMarkdown as String?) ?? '';

    return Column(
      children: [
        if (history.length > 1)
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            child: DropdownButton<int>(
              value: _selectedIndex,
              isExpanded: true,
              items: [
                for (int i = 0; i < history.length; i++)
                  DropdownMenuItem(
                    value: i,
                    child: Text(
                      '${history[i].date.toIso8601String().split('T').first}'
                      '  (${history[i].periodStart.toIso8601String().split('T').first}'
                      ' → ${history[i].periodEnd.toIso8601String().split('T').first})',
                    ),
                  ),
              ],
              onChanged: (val) => setState(() => _selectedIndex = val ?? 0),
            ),
          ),
        Expanded(
          child: md.isEmpty
              ? const Center(child: Text('אין דוח זמין'))
              : Directionality(
                  textDirection: TextDirection.rtl,
                  child: Markdown(data: md),
                ),
        ),
      ],
    );
  }
}

class _TrendsTab extends StatelessWidget {
  const _TrendsTab();

  static const _chartConfig = [
    ('avg_sleep_hours', 'שינה', 'שעות', Colors.indigo),
    ('avg_resting_hr', 'RHR', 'bpm', Colors.red),
    ('avg_hrv_nightly', 'HRV', 'ms', Colors.teal),
    ('weight_kg', 'משקל', 'ק"ג', Colors.brown),
    ('avg_daily_steps', 'צעדים', 'ממוצע', Colors.green),
    ('avg_body_battery_peak', 'Body Battery', 'שיא', Colors.orange),
  ];

  @override
  Widget build(BuildContext context) {
    final summaryProvider = context.watch<SummaryProvider>();
    final trends = summaryProvider.extractTrendData();

    final hasData = trends.values.any((list) => list.isNotEmpty);
    if (!hasData) {
      return const Center(child: Text('בקרוב'));
    }

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        for (final (metric, title, unit, color) in _chartConfig)
          Padding(
            padding: const EdgeInsets.only(bottom: 12),
            child: TrendChart(
              title: title,
              unit: unit,
              color: color,
              data: trends[metric] ?? [],
            ),
          ),
      ],
    );
  }
}

class _TimelineTab extends StatefulWidget {
  const _TimelineTab();

  @override
  State<_TimelineTab> createState() => _TimelineTabState();
}

class _TimelineTabState extends State<_TimelineTab> {
  List<TimelineEvent> _events = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    Future.microtask(() async {
      try {
        final api = context.read<SummaryProvider>();
        // Load timeline from API through a direct call
        final client = Provider.of<ApiClient>(context, listen: false);
        final events = await client.getTimeline();
        if (mounted) setState(() { _events = events; _loading = false; });
      } catch (_) {
        if (mounted) setState(() => _loading = false);
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) return const Center(child: CircularProgressIndicator());
    if (_events.isEmpty) {
      return const Center(child: Text('אין אירועים בציר הזמן'));
    }

    // Sort newest first
    final sorted = [..._events]..sort((a, b) => b.date.compareTo(a.date));

    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: sorted.length,
      itemBuilder: (context, index) {
        final event = sorted[index];
        return _buildTimelineItem(context, event, isLast: index == sorted.length - 1);
      },
    );
  }

  Widget _buildTimelineItem(BuildContext context, TimelineEvent event, {bool isLast = false}) {
    final color = _categoryColor(event.category);
    final icon = _severityIcon(event.severity);

    return IntrinsicHeight(
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Timeline line + dot
          SizedBox(
            width: 40,
            child: Column(
              children: [
                Container(
                  width: 16,
                  height: 16,
                  decoration: BoxDecoration(
                    color: color,
                    shape: BoxShape.circle,
                  ),
                  child: Icon(icon, size: 10, color: Colors.white),
                ),
                if (!isLast)
                  Expanded(
                    child: Container(width: 2, color: color.withAlpha(60)),
                  ),
              ],
            ),
          ),
          // Content
          Expanded(
            child: Padding(
              padding: const EdgeInsets.only(bottom: 16),
              child: Card(
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        event.date.toIso8601String().split('T').first,
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                      const SizedBox(height: 4),
                      Text(
                        event.titleHe,
                        style: Theme.of(context).textTheme.titleSmall,
                      ),
                      if (event.detailHe.isNotEmpty) ...[
                        const SizedBox(height: 4),
                        Text(event.detailHe),
                      ],
                    ],
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Color _categoryColor(String category) {
    switch (category) {
      case 'medical': return Colors.red;
      case 'milestone': return Colors.green;
      case 'medication': return Colors.blue;
      case 'lifestyle': return Colors.purple;
      default: return Colors.grey;
    }
  }

  IconData _severityIcon(String severity) {
    switch (severity) {
      case 'critical': return Icons.warning;
      case 'warning': return Icons.info;
      case 'positive': return Icons.star;
      default: return Icons.circle;
    }
  }
}

class _LabTrendsTab extends StatefulWidget {
  const _LabTrendsTab();

  @override
  State<_LabTrendsTab> createState() => _LabTrendsTabState();
}

class _LabTrendsTabState extends State<_LabTrendsTab> {
  List<LabTrend> _trends = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    Future.microtask(() async {
      try {
        final client = Provider.of<ApiClient>(context, listen: false);
        final trends = await client.getLabTrends();
        if (mounted) setState(() { _trends = trends; _loading = false; });
      } catch (_) {
        if (mounted) setState(() => _loading = false);
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) return const Center(child: CircularProgressIndicator());
    if (_trends.isEmpty) {
      return const Center(child: Text('אין נתוני מעבדה עדיין'));
    }

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        for (final trend in _trends)
          if (trend.values.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: TrendChart(
                title: trend.displayNameHe.isNotEmpty ? trend.displayNameHe : trend.metric,
                unit: trend.values.first.unit,
                color: _labColor(trend.metric),
                data: trend.values
                    .map((v) => (v.date, v.value))
                    .toList(),
              ),
            ),
      ],
    );
  }

  Color _labColor(String metric) {
    switch (metric.toLowerCase()) {
      case 'ldl': return Colors.red;
      case 'hdl': return Colors.blue;
      case 'hba1c': return Colors.purple;
      case 'vitamin_d': return Colors.orange;
      case 'glucose': return Colors.teal;
      default: return Colors.grey;
    }
  }
}