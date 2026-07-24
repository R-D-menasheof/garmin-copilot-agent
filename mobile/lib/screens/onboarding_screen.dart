import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/auth_provider.dart';
import '../services/api_client.dart';

/// First-run onboarding wizard, shown when the profile isn't onboarded yet.
///
/// Collects the essentials (date of birth, sex, height, primary goal) and
/// submits them via PATCH /v1/profile with onboarded=true.
class OnboardingScreen extends StatefulWidget {
  const OnboardingScreen({super.key});

  @override
  State<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends State<OnboardingScreen> {
  final _heightCtrl = TextEditingController();
  final _goalCtrl = TextEditingController();
  DateTime? _dob;
  String _sex = 'Male';
  bool _saving = false;

  @override
  void dispose() {
    _heightCtrl.dispose();
    _goalCtrl.dispose();
    super.dispose();
  }

  Future<void> _pickDob() async {
    final now = DateTime.now();
    final picked = await showDatePicker(
      context: context,
      initialDate: DateTime(now.year - 30),
      firstDate: DateTime(now.year - 100),
      lastDate: now,
    );
    if (picked != null) setState(() => _dob = picked);
  }

  Future<void> _submit() async {
    setState(() => _saving = true);
    final api = context.read<ApiClient>();
    final auth = context.read<AuthProvider>();

    final changes = <String, dynamic>{
      'onboarded': true,
      if (_dob != null)
        'date_of_birth':
            '${_dob!.year}-${_dob!.month.toString().padLeft(2, '0')}-${_dob!.day.toString().padLeft(2, '0')}',
      'sex': _sex,
      if (int.tryParse(_heightCtrl.text) != null)
        'height_cm': int.parse(_heightCtrl.text),
      if (_goalCtrl.text.trim().isNotEmpty) 'goals': [_goalCtrl.text.trim()],
    };

    try {
      await api.patchProfile(changes);
      auth.setOnboarded(true);
    } catch (_) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('שמירה נכשלה. נסה שוב.')),
        );
      }
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    final name = auth.displayName.isNotEmpty ? auth.displayName : 'ברוך הבא';

    return Scaffold(
      appBar: AppBar(title: const Text('הגדרה ראשונית')),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Text('שלום $name!', style: Theme.of(context).textTheme.headlineSmall),
          const SizedBox(height: 8),
          const Text('כמה פרטים כדי להתאים לך את Vitalis:'),
          const SizedBox(height: 24),
          ListTile(
            key: const ValueKey('onboard-dob'),
            title: const Text('תאריך לידה'),
            subtitle: Text(_dob == null
                ? 'בחר תאריך'
                : '${_dob!.day}/${_dob!.month}/${_dob!.year}'),
            trailing: const Icon(Icons.calendar_today),
            onTap: _pickDob,
          ),
          const SizedBox(height: 8),
          Row(
            children: [
              const Text('מין:  '),
              const SizedBox(width: 8),
              DropdownButton<String>(
                key: const ValueKey('onboard-sex'),
                value: _sex,
                items: const [
                  DropdownMenuItem(value: 'Male', child: Text('זכר')),
                  DropdownMenuItem(value: 'Female', child: Text('נקבה')),
                ],
                onChanged: (v) => setState(() => _sex = v ?? 'Male'),
              ),
            ],
          ),
          const SizedBox(height: 8),
          TextField(
            key: const ValueKey('onboard-height'),
            controller: _heightCtrl,
            keyboardType: TextInputType.number,
            decoration: const InputDecoration(
              labelText: 'גובה (ס״מ)',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 16),
          TextField(
            key: const ValueKey('onboard-goal'),
            controller: _goalCtrl,
            decoration: const InputDecoration(
              labelText: 'מטרה עיקרית',
              hintText: 'לדוגמה: ירידה במשקל',
              border: OutlineInputBorder(),
            ),
          ),
          const SizedBox(height: 32),
          FilledButton(
            key: const ValueKey('onboard-submit'),
            onPressed: _saving ? null : _submit,
            style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(52)),
            child: _saving
                ? const CircularProgressIndicator()
                : const Text('סיום והתחלה'),
          ),
        ],
      ),
    );
  }
}
