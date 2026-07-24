import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../providers/auth_provider.dart';
import '../providers/biometrics_provider.dart';

/// Settings screen — account, API key, sync status, preferences.
class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final biometrics = context.watch<BiometricsProvider>();
    final auth = context.watch<AuthProvider>();

    final rawName = auth.displayName.trim();
    final hasName = rawName.isNotEmpty && rawName.toLowerCase() != 'unknown';
    final nameLabel = hasName ? rawName : 'הגדר את שמך';

    return Scaffold(
      appBar: AppBar(title: const Text('הגדרות')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // Signed-in account indicator.
          Card(
            child: Column(
              children: [
                ListTile(
                  leading: CircleAvatar(
                    child: Text(
                      hasName ? rawName.characters.first.toUpperCase() : '?',
                    ),
                  ),
                  title: Text(
                    nameLabel,
                    style: TextStyle(
                      fontWeight: FontWeight.bold,
                      color: hasName ? null : Colors.grey,
                    ),
                  ),
                  subtitle: Text(
                    auth.email.isNotEmpty ? auth.email : 'מחובר',
                    textDirection: TextDirection.ltr,
                  ),
                  trailing: IconButton(
                    icon: const Icon(Icons.edit),
                    tooltip: 'ערוך שם',
                    onPressed: () => _editName(context, auth, hasName ? rawName : ''),
                  ),
                ),
                const Divider(height: 1),
                ListTile(
                  leading: const Icon(Icons.logout, color: Colors.red),
                  title: const Text('התנתקות',
                      style: TextStyle(color: Colors.red)),
                  onTap: () => _confirmSignOut(context, auth),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
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
          const Divider(height: 24),
          ListTile(
            leading: const Icon(Icons.person_outline),
            title: const Text('הפרופיל שלי'),
            subtitle: const Text('עריכת פרטים אישיים, מטרות, תרופות'),
            trailing: const Icon(Icons.chevron_left),
            onTap: () => context.push('/profile'),
          ),
          ListTile(
            leading: const Icon(Icons.folder_shared_outlined),
            title: const Text('מסמכים רפואיים'),
            subtitle: const Text('העלאה וצפייה במסמכים רפואיים'),
            trailing: const Icon(Icons.chevron_left),
            onTap: () => context.push('/medical'),
          ),
        ],
      ),
    );
  }

  Future<void> _editName(
      BuildContext context, AuthProvider auth, String current) async {
    final controller = TextEditingController(text: current);
    final name = await showDialog<String>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('השם שלך'),
        content: TextField(
          controller: controller,
          autofocus: true,
          textCapitalization: TextCapitalization.words,
          decoration: const InputDecoration(hintText: 'לדוגמה: רועי'),
          onSubmitted: (v) => Navigator.pop(ctx, v.trim()),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('ביטול'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, controller.text.trim()),
            child: const Text('שמור'),
          ),
        ],
      ),
    );
    if (name != null && name.isNotEmpty && context.mounted) {
      try {
        await auth.updateDisplayName(name);
      } catch (e) {
        if (context.mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('שמירת השם נכשלה: $e')),
          );
        }
      }
    }
  }

  Future<void> _confirmSignOut(BuildContext context, AuthProvider auth) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('התנתקות'),
        content: const Text('להתנתק מהחשבון?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('ביטול'),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('התנתק'),
          ),
        ],
      ),
    );
    if (ok == true) {
      await auth.signOut();
    }
  }
}
