import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/biometrics_provider.dart';

/// Settings screen — API key, sync status, preferences.
class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final biometrics = context.watch<BiometricsProvider>();

    return Scaffold(
      appBar: AppBar(title: const Text('הגדרות')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          const TextField(
            decoration: InputDecoration(
              labelText: 'API Key',
              border: OutlineInputBorder(),
            ),
            obscureText: true,
          ),
          const SizedBox(height: 16),
          ListTile(
            title: const Text('סטטוס סנכרון'),
            subtitle: Text(biometrics.freshnessLabel),
            trailing: const Icon(Icons.sync),
            onTap: biometrics.loading ? null : () => biometrics.loadToday(),
          ),
          ListTile(
            title: const Text('מקור נתונים'),
            subtitle: Text(biometrics.sourceLabel),
            trailing: const Icon(Icons.health_and_safety_outlined),
          ),
          ListTile(
            title: const Text('רענון אחרון'),
            subtitle: Text(biometrics.lastUpdatedLabel),
            trailing: const Icon(Icons.schedule),
          ),
        ],
      ),
    );
  }
}
