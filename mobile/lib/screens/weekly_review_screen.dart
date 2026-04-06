import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/summary_provider.dart';

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
      context.read<SummaryProvider>().loadSummaryHistory(limit: 6);
    });
  }

  @override
  Widget build(BuildContext context) {
    final summaryProvider = context.watch<SummaryProvider>();
    final history = summaryProvider.summaryHistory;

    return Scaffold(
      appBar: AppBar(title: const Text('סקירה שבועית')),
      body: summaryProvider.loading && history.isEmpty
          ? const Center(child: CircularProgressIndicator())
          : history.isEmpty
              ? const Center(child: Text('אין עדיין סקירות זמינות'))
              : ListView.separated(
                  padding: const EdgeInsets.all(16),
                  itemCount: history.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 12),
                  itemBuilder: (context, index) {
                    final summary = history[index];
                    return Card(
                      child: Padding(
                        padding: const EdgeInsets.all(16),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              summary.date.toIso8601String().split('T').first,
                              style: Theme.of(context).textTheme.titleMedium,
                            ),
                            const SizedBox(height: 8),
                            for (final trend in summary.trends) ...[
                              Text(trend),
                              const SizedBox(height: 4),
                            ],
                            if (summary.recommendations.isNotEmpty) ...[
                              const SizedBox(height: 8),
                              Text(
                                summary.recommendations.first.title,
                                style: Theme.of(context).textTheme.bodyLarge,
                              ),
                              const SizedBox(height: 4),
                              Text(summary.recommendations.first.detail),
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