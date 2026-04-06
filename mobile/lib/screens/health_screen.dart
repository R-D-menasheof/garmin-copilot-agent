import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/biometrics_provider.dart';

/// Health data screen — shows current biometrics from Health Connect / Garmin.
class HealthScreen extends StatefulWidget {
  const HealthScreen({super.key});

  @override
  State<HealthScreen> createState() => _HealthScreenState();
}

class _HealthScreenState extends State<HealthScreen> {
  @override
  void initState() {
    super.initState();
    // Load data on screen open
    Future.microtask(() {
      context.read<BiometricsProvider>().loadToday();
    });
  }

  @override
  Widget build(BuildContext context) {
    final bio = context.watch<BiometricsProvider>();
    final theme = Theme.of(context);
    final latest = bio.latest;

    return Scaffold(
      appBar: AppBar(
        title: const Text('נתוני בריאות'),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh),
            onPressed: bio.loading ? null : () => bio.loadToday(),
            tooltip: 'רענון',
          ),
        ],
      ),
      body: bio.loading
          ? const Center(child: CircularProgressIndicator())
          : latest == null
              ? _HealthStatusView(
                  message: bio.statusMessage ?? 'אין נתונים זמינים',
                  icon: bio.state == BiometricsState.permissionDenied
                      ? Icons.lock_outline
                      : bio.state == BiometricsState.error
                          ? Icons.error_outline
                          : Icons.health_and_safety_outlined,
                  actionLabel: bio.primaryActionLabel ?? 'נסה שוב',
                  onAction: () => bio.performPrimaryAction(),
                )
              : RefreshIndicator(
                  onRefresh: () => bio.loadToday(),
                  child: ListView(
                    padding: const EdgeInsets.all(16),
                    children: [
                      // Source indicator
                      if (bio.usesDemoData)
                        Card(
                          color: theme.colorScheme.tertiaryContainer,
                          child: const Padding(
                            padding: EdgeInsets.all(12),
                            child: Row(
                              children: [
                                Icon(Icons.info_outline, size: 20),
                                SizedBox(width: 8),
                                Expanded(
                                  child: Text(
                                    'מצב הדגמה — נתונים לדוגמה. '
                                    'חבר מכשיר Garmin דרך Health Connect לנתונים אמיתיים.',
                                    style: TextStyle(fontSize: 13),
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                      if (bio.statusMessage != null && !bio.usesDemoData)
                        Card(
                          color: theme.colorScheme.secondaryContainer,
                          child: Padding(
                            padding: const EdgeInsets.all(12),
                            child: Text(bio.statusMessage!),
                          ),
                        ),
                      Card(
                        child: Padding(
                          padding: const EdgeInsets.all(12),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text('מקור: ${bio.sourceLabel}'),
                              const SizedBox(height: 4),
                              Text('סטטוס: ${bio.freshnessLabel}'),
                              const SizedBox(height: 4),
                              Text('רענון אחרון: ${bio.lastUpdatedLabel}'),
                            ],
                          ),
                        ),
                      ),
                      if (bio.usesDemoData || bio.statusMessage != null)
                        const SizedBox(height: 16),

                      // ── Activity ───────────────────────────
                      _SectionHeader(title: 'פעילות', icon: Icons.directions_walk),
                      const SizedBox(height: 8),
                      Row(children: [
                        Expanded(child: _MetricCard(title: 'צעדים', value: bio.stepsFormatted, icon: Icons.directions_walk, color: Colors.blue)),
                        const SizedBox(width: 8),
                        Expanded(child: _MetricCard(title: 'קלוריות פעילות', value: bio.activeCalFormatted, icon: Icons.local_fire_department, color: Colors.orange, suffix: 'kcal')),
                      ]),
                      const SizedBox(height: 8),
                      Row(children: [
                        Expanded(child: _MetricCard(title: 'מרחק', value: bio.distanceFormatted, icon: Icons.straighten, color: Colors.blueGrey)),
                        const SizedBox(width: 8),
                        Expanded(child: _MetricCard(title: 'קומות', value: bio.floorsFormatted, icon: Icons.stairs, color: Colors.brown)),
                      ]),
                      const SizedBox(height: 8),
                      Row(children: [
                        Expanded(child: _MetricCard(title: 'דקות פעילות', value: bio.exerciseMinFormatted, icon: Icons.timer, color: Colors.green, suffix: 'min')),
                        const SizedBox(width: 8),
                        Expanded(child: _MetricCard(title: 'דקות עצימות', value: bio.intensityMinFormatted, icon: Icons.speed, color: Colors.deepOrange, suffix: 'min')),
                      ]),
                      const SizedBox(height: 8),
                      Row(children: [
                        Expanded(child: _MetricCard(title: 'סה"כ קלוריות', value: bio.totalCalFormatted, icon: Icons.whatshot, color: Colors.red, suffix: 'kcal')),
                        const SizedBox(width: 8),
                        const Expanded(child: SizedBox()),
                      ]),

                      const SizedBox(height: 20),

                      // ── Heart ──────────────────────────────
                      _SectionHeader(title: 'לב', icon: Icons.favorite),
                      const SizedBox(height: 8),
                      Row(children: [
                        Expanded(child: _MetricCard(title: 'דופק במנוחה', value: bio.restingHrFormatted, icon: Icons.favorite, color: Colors.red, suffix: 'bpm')),
                        const SizedBox(width: 8),
                        Expanded(child: _MetricCard(title: 'דופק ממוצע', value: bio.avgHrFormatted, icon: Icons.favorite_border, color: Colors.redAccent, suffix: 'bpm')),
                      ]),
                      const SizedBox(height: 8),
                      Row(children: [
                        Expanded(child: _MetricCard(title: 'דופק מקסימלי', value: bio.maxHrFormatted, icon: Icons.flash_on, color: Colors.deepOrange, suffix: 'bpm')),
                        const SizedBox(width: 8),
                        Expanded(child: _MetricCard(title: 'HRV', value: bio.hrvFormatted, icon: Icons.show_chart, color: Colors.purple, suffix: 'ms')),
                      ]),

                      const SizedBox(height: 20),

                      // ── Sleep ──────────────────────────────
                      _SectionHeader(title: 'שינה', icon: Icons.bedtime),
                      const SizedBox(height: 8),
                      Row(children: [
                        Expanded(child: _MetricCard(title: 'סה"כ שינה', value: bio.sleepFormatted, icon: Icons.bedtime, color: Colors.indigo)),
                        const SizedBox(width: 8),
                        Expanded(child: _MetricCard(title: 'ציון שינה', value: bio.sleepScoreFormatted, icon: Icons.star, color: Colors.amber, suffix: '/100')),
                      ]),
                      const SizedBox(height: 8),
                      Row(children: [
                        Expanded(child: _MetricCard(title: 'Deep', value: bio.deepSleepFormatted, icon: Icons.nightlight, color: Colors.indigo.shade800)),
                        const SizedBox(width: 8),
                        Expanded(child: _MetricCard(title: 'REM', value: bio.remSleepFormatted, icon: Icons.remove_red_eye, color: Colors.deepPurple)),
                      ]),
                      const SizedBox(height: 8),
                      Row(children: [
                        Expanded(child: _MetricCard(title: 'Light', value: bio.lightSleepFormatted, icon: Icons.wb_twilight, color: Colors.blue.shade300)),
                        const SizedBox(width: 8),
                        Expanded(child: _MetricCard(title: 'ער', value: bio.awakeSleepFormatted, icon: Icons.visibility, color: Colors.grey)),
                      ]),

                      const SizedBox(height: 20),

                      // ── Vitals ─────────────────────────────
                      _SectionHeader(title: 'מדדים חיוניים', icon: Icons.monitor_heart),
                      const SizedBox(height: 8),
                      Row(children: [
                        Expanded(child: _MetricCard(title: 'SpO2', value: bio.spo2Formatted, icon: Icons.air, color: Colors.teal, suffix: '%')),
                        const SizedBox(width: 8),
                        Expanded(child: _MetricCard(title: 'טמפרטורה', value: bio.bodyTempFormatted, icon: Icons.thermostat, color: Colors.orange, suffix: 'C')),
                      ]),
                      const SizedBox(height: 8),
                      Row(children: [
                        Expanded(child: _MetricCard(title: 'נשימות/דקה', value: bio.respRateFormatted, icon: Icons.air, color: Colors.cyan)),
                        const SizedBox(width: 8),
                        Expanded(child: _MetricCard(title: 'לחץ דם', value: bio.bpFormatted, icon: Icons.bloodtype, color: Colors.red.shade800, suffix: 'mmHg')),
                      ]),

                      const SizedBox(height: 20),

                      // ── Body ───────────────────────────────
                      _SectionHeader(title: 'גוף', icon: Icons.accessibility_new),
                      const SizedBox(height: 8),
                      Row(children: [
                        Expanded(child: _MetricCard(title: 'משקל', value: bio.weightFormatted, icon: Icons.monitor_weight, color: Colors.green, suffix: 'kg')),
                        const SizedBox(width: 8),
                        Expanded(child: _MetricCard(title: 'BMR', value: bio.bmrFormatted, icon: Icons.bolt, color: Colors.deepPurple, suffix: 'kcal/day')),
                      ]),
                      const SizedBox(height: 8),
                      Row(children: [
                        Expanded(child: _MetricCard(title: 'אחוז שומן', value: bio.bodyFatFormatted, icon: Icons.pie_chart, color: Colors.orange)),
                        const SizedBox(width: 8),
                        Expanded(child: _MetricCard(title: 'BMI', value: bio.bmiFormatted, icon: Icons.scale, color: Colors.blueGrey)),
                      ]),

                      const SizedBox(height: 20),

                      // ── Hydration ──────────────────────────
                      _SectionHeader(title: 'שתייה', icon: Icons.water_drop),
                      const SizedBox(height: 8),
                      Row(children: [
                        Expanded(child: _MetricCard(title: 'מים', value: bio.waterFormatted, icon: Icons.water_drop, color: Colors.lightBlue)),
                        const SizedBox(width: 8),
                        const Expanded(child: SizedBox()),
                      ]),

                      const SizedBox(height: 24),
                    ],
                  ),
                ),
    );
  }
}

class _HealthStatusView extends StatelessWidget {
  const _HealthStatusView({
    required this.message,
    required this.icon,
    required this.actionLabel,
    required this.onAction,
  });

  final String message;
  final IconData icon;
  final String actionLabel;
  final VoidCallback onAction;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 44),
            const SizedBox(height: 12),
            Text(
              message,
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodyLarge,
            ),
            const SizedBox(height: 16),
            FilledButton(
              onPressed: onAction,
              child: Text(actionLabel),
            ),
          ],
        ),
      ),
    );
  }
}

class _SectionHeader extends StatelessWidget {
  final String title;
  final IconData icon;

  const _SectionHeader({required this.title, required this.icon});

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Icon(icon, size: 20, color: Theme.of(context).colorScheme.primary),
        const SizedBox(width: 8),
        Text(
          title,
          style: Theme.of(context).textTheme.titleMedium?.copyWith(
                fontWeight: FontWeight.bold,
              ),
        ),
      ],
    );
  }
}

class _MetricCard extends StatelessWidget {
  final String title;
  final String value;
  final IconData icon;
  final Color color;
  final String? suffix;

  const _MetricCard({
    required this.title,
    required this.value,
    required this.icon,
    required this.color,
    this.suffix,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 1,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(icon, size: 18, color: color),
                const SizedBox(width: 6),
                Expanded(
                  child: Text(
                    title,
                    style: Theme.of(context).textTheme.bodySmall,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 8),
            Text(
              value,
              style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                    fontWeight: FontWeight.bold,
                    color: color,
                  ),
            ),
            if (suffix != null)
              Text(
                suffix!,
                style: Theme.of(context).textTheme.bodySmall,
              ),
          ],
        ),
      ),
    );
  }
}
